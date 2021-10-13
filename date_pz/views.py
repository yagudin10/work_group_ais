from django.shortcuts import render
from dotenv import dotenv_values
from sqlalchemy import create_engine
import io
import json
import os
import pandas as pd
import pyodbc
import pymysql
import re
import requests
from datetime import timedelta
import datetime
import time
from requests.auth import HTTPBasicAuth
from requests.sessions import session
from django.http import HttpResponse
from io import BytesIO
from .forms import DateForm, DateFormAppointment, MFCForm, DateFormMRS
from .models import MFC
from bs4 import BeautifulSoup

# a function that gets from Qmatic
def get_info_from_site(link, params=None):
    return requests.get(
        link,
        auth=HTTPBasicAuth(os.getenv("USER_QM"),
        os.getenv("PASS_QM")),
        params=params
    )

# a function that gets the customer's name from the appointment
def get_fio(id):
    link = '{}/v1/customers/{}'.format(os.getenv("LINK"), id)
    r = get_info_from_site(link)
    return (json.loads(r.text)["customer"]["name"])

# reading SQL scripts
def readSqlScript(filename):
  sql_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'scripts/'
  )
  sql_file = io.open(
    os.path.join(sql_path, '{}.sql'.format(filename)),
    mode='r',
    encoding='utf-8'
  )
  sqlScript = sql_file.read()
  sql_file.close()
  return sqlScript

# a function that returns .xlsx-file as response
def returnxls(wb, filename):
    response = HttpResponse(
      wb,
      content_type='application/vnd.openxmlformats-officedocument.\
                    spreadsheetml.sheet'
    )
    response['Content-Disposition']='attachment; filename="{}.xlsx"'.format(filename)
    return response


def index(request):
    return render(request, 'index.html')


def test(request):
    return render(request, 'test.html')

# returns a info of the nearest date of appointment for each branch
def nearest_appointment_date(request):
    link_1 = '{}/v2/branches'.format(os.getenv("LINK1"))
    link_branches = '{}/v2/branches/available'.format(os.getenv("LINK1"))
    link_services = '{}/v1/services'.format(os.getenv("LINK1"))
    branches = get_info_from_site(link_branches)
    services = get_info_from_site(link_services)
    branch_list = pd.json_normalize(
        json.loads(branches.text)['branch'] #load only dict with a key 'branch' 
    )
    serv_list = pd.json_normalize(
        json.loads(services.text)['serviceList']
    )
    result = pd.DataFrame(
        columns=['Филиал', 'Услуга', 'Ближайшая свободная дата']
    )
    for index_br, row_br in branch_list.iterrows():
        for index_s, row_s in serv_list.iterrows():
            link_w_br = '{}/{}/dates;servicePublicId={}'.format(
                link_1, 
                row_br['publicId'], 
                row_s['publicId']
                )
            dates = get_info_from_site(link_w_br)
            if dates.status_code == 500:
                continue
            else:
                date = json.loads(dates.text)["dates"]
                date_br = 'нет даты'
                if len(date) != 0:
                    date_br = date[0][:10]
                data = {'Филиал': row_br['name'],
                        'Услуга': row_s['name'],
                        'Ближайшая свободная дата': date_br}
                new_row = pd.Series(data=data)
                result = result.append(new_row, ignore_index=True)
    sio = BytesIO()
    PandasWriter = pd.ExcelWriter(sio, engine='xlsxwriter')
    result.to_excel(PandasWriter, index=None)
    # Formats Excel sheet
    workbook = PandasWriter.book
    worksheet = PandasWriter.sheets['Sheet1']
    worksheet.set_column('A:A', 64)
    worksheet.set_column('B:B', 71)
    worksheet.set_column('C:C', 27)
    PandasWriter.save()
    sio.seek(0)
    workbook = sio.getvalue()
    return returnxls(workbook, 'test')


def create_table(request):
    if request.method == 'GET':
        date_form = DateFormAppointment
        return render(
            request, 
            'app.html',
            {'date_form': date_form}
        )
    if request.method == 'POST':
        form = DateFormAppointment(request.POST)
        if form.is_valid():
            y = form.cleaned_data['date1_field']
            x = form.cleaned_data['date2_field']
        sz = BytesIO()
        PandasWriter = pd.ExcelWriter(sz, engine='xlsxwriter')
        z = (x - y).days + 1
        for i in range(z):
            date1 = (y + timedelta(i)).strftime('%Y-%m-%d')
            date2 = (y + timedelta(i+1)).strftime('%Y-%m-%d')
            tab(date1, date2, PandasWriter)
        PandasWriter.save()
        sz.seek(0)
        workbook = sz.getvalue()
        return returnxls(workbook, 'qmatic')

# a function that gets all appointments for the selected period
def tab(date_1, date_2, PdWriter):
    qmatic = '{}/v1/appointments'.format(os.getenv("LINK"))
    data = {
        'start': date_1,
        'end': date_2,
        'timeZoneBranchId': '10'
    }
    text = get_info_from_site(qmatic, params=data)
    appList = json.loads(text.text)["appointmentList"]
    df1 = pd.json_normalize(
        appList, 
        record_path=['customers'], 
        meta=[
            'id', 
            ['branch', 'name'], 
            ['resource', 'name'], 
            'start', 
            'end'
        ], 
        record_prefix='customers.'
    )
    df1 = df1[[
        'start', 
        'end', 
        'branch.name', 
        'resource.name', 
        'id',
        'customers.name', 
        'customers.email', 
        'customers.phone'
    ]]
    df2 = pd.json_normalize(
        appList, 
        record_path=['services'],
        meta=['id'],
        record_prefix='services.'
    )
    df2 = df2[['id', 'services.name']]
    df = pd.merge(
        df1, 
        df2, 
        left_on='id', 
        right_on='id'
    )
    df['date'] = pd.to_datetime(df['start']).dt.date
    df['start'] = pd.to_datetime(df['start']).dt.time
    df['end'] = pd.to_datetime(df['end']).dt.time
    df.to_excel(PdWriter, index=None, sheet_name=data['start'])
    # Formats Excel sheet
    workbook = PdWriter.book
    worksheet = PdWriter.sheets[data['start']]
    worksheet.set_column('A:B', 7.5)
    worksheet.set_column('C:C', 64)
    worksheet.set_column('D:D', 44)
    worksheet.set_column('E:E', 7.57)
    worksheet.set_column('F:F', 39)
    worksheet.set_column('G:H', 18)
    worksheet.set_column('I:I', 70.7)
    worksheet.set_column('J:J', 10)


def talon(request):
    if request.method == 'GET':
        # Updating list of branches
        cnxn = pyodbc.connect(**dotenv_values(".env.qmatic"))
        cursor = cnxn.cursor()
        query = "SELECT DISTINCT name FROM stat.dim_branch WHERE id NOT IN (2160, 2072, 2114)"
        df_mfc = pd.read_sql(query, cnxn)
        MFC.objects.all().delete()
        for item in df_mfc['name']:
            MFC.objects.create(name = item)
        model_context = MFC.objects.all()
        date_form = DateForm
        return render(request, 'talon.html', 
                      {'model_context': model_context, 
                       'date_form': date_form})
    if request.method == 'POST':
        form = MFCForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
        form1 = DateForm(request.POST)
        form1.is_valid()
        date = form1.cleaned_data['date_field']
        date_new = date.strftime('%Y%m%d')
        cnxn = pyodbc.connect(**dotenv_values(".env.qmatic"))
        cursor = cnxn.cursor()
        # Reading SQL script and adding selected values into them
        query = readSqlScript('talon').format(date_new, name)
        df = pd.read_sql(query, cnxn)
        df['ID клиента'] = df['ID клиента'].astype('Int32').fillna(-1)
        df['ФИО клиента'] = df['ID клиента'].astype('str')
        for index, row in df.iterrows():
            df.loc[index, 'ФИО клиента'] = get_fio(
                df.loc[index, 'ФИО клиента']
                ) if df.loc[index, 'ID клиента'] != -1 else None
        sio = BytesIO()

        PandasWriter = pd.ExcelWriter(sio, engine='xlsxwriter')
        df.to_excel(PandasWriter, index=None)
        PandasWriter.save()
        sio.seek(0)
        workbook = sio.getvalue()
        return returnxls(workbook, 'talon')

# autorization to SIER (getting an access token)
def sier():
    link = '{}/authorize'.format(os.getenv("LINK2"))
    r = requests.post(link, data={**dotenv_values(".env.sier")})
    accessToken = json.loads(r.text)['accessToken']
    refreshToken = json.loads(r.text)['refreshToken']
    data = {
    'accessToken': accessToken,
    'orgId': '2cda1b28-c295-41b2-a48d-2dea952ab82c'
    }
    link1 = '{}/selectOrg'.format(os.getenv("LINK2"))
    r1 = requests.post(link1, data=data)
    newaccessToken = json.loads(r1.text)['accessToken']
    return newaccessToken


def ros_administ(request):    
    if request.method == 'GET':
        date_form = DateFormAppointment
        return render(request, 'adm.html', 
                      {'date_form': date_form})
    if request.method == 'POST':
        form = DateFormAppointment(request.POST)
        if form.is_valid():
            date_begin = form.cleaned_data['date1_field']
            date_end = form.cleaned_data['date2_field']
        newaccessToken = sier()
        headers = {
            'content-type': 'application/json',
            'authorization': 'Bearer {}'.format(newaccessToken),
        }
        data = {
            "search": {
                "search": [
                {
                    "orSubConditions": [
                    {
                    "field": "subservices.serviceId",
                    "operator": "eq",
                    "value": "0198"
                    },
                    {
                    "field": "subservices.serviceId",
                    "operator": "eq",
                    "value": "2626"
                    },
                    {
                    "field": "subservices.serviceId",
                    "operator": "eq",
                    "value": "3080"
                    }
                    ]
                },
                {
                    "field": "dateRegister",
                    "operator": "le",
                    "value": (date_end+timedelta(1)).strftime('%Y-%m-%d')
                },
                {
                    "field": "dateRegister",
                    "operator": "ge",
                    "value": date_begin.strftime('%Y-%m-%d')
                }
                ],
                "textSearch": "Администрация || Администрации"
            },
            "size": 2000,
            "page": 0,
            "sort": "dateRegister,ASC",
            "prj": "appealList"
        }
        link2 = '{}/api/v1/search/appeals'.format(os.getenv("LINK2"))
        data_to_send = json.dumps(data).encode("utf-8")
        r2 = requests.post(link2, headers=headers, data=data_to_send)
        data = json.loads(r2.text)['content']
        df1 = pd.json_normalize(
            data, 
            record_path=['objects'], 
            meta = [
                'dateRegister',
                'shortNumber', 
                ['status', 'name'],
                ['unit', 'shortName']
            ],
            record_prefix='obj.'
        )
        df1['dateRegister'] = pd.to_datetime(df1['dateRegister']).dt.date
        df1 = df1[[
            'dateRegister', 
            'shortNumber', 
            'status.name', 
            'unit.shortName', 
            'obj.shortHeader'
        ]]
        df2 = pd.json_normalize(
            data, 
            record_path=['subservices'], 
            meta = ['shortNumber'],
            record_prefix= 'subs.'
        )
        df2 = df2[[
            'shortNumber', 
            'subs.externalNumber', 
            'subs.shortTitle'
        ]]
        result = pd.merge(
            df1, 
            df2, 
            left_on='shortNumber', 
            right_on='shortNumber'
        )
        result = result.rename(
            columns={
                'dateRegister':'Дата регистрации',
                'shortNumber':'Номер дела',
                'status.name':'Статус дела',
                'subs.shortTitle':'Наименование услуги',
                'unit.shortName':'Наименование отделения',
                'obj.shortHeader': 'Заявитель',
                'subs.externalNumber':'Внешний номер'
            }
        )
        sio = BytesIO()
        PandasWriter = pd.ExcelWriter(sio, engine='xlsxwriter')
        result.to_excel(PandasWriter, index=None)
        # Formats Excel sheet
        workbook = PandasWriter.book
        worksheet = PandasWriter.sheets['Sheet1']
        worksheet.set_column('A:A', 11)
        worksheet.set_column('B:B', 9)
        worksheet.set_column('C:C', 27)
        worksheet.set_column('D:D', 85)
        worksheet.set_column('E:E', 85)
        worksheet.set_column('F:F', 23)
        PandasWriter.save()
        sio.seek(0)
        workbook = sio.getvalue()
        return returnxls(workbook, 'rosreestr_OMSU')

# a function that gets an information of all documents in PKPVD program
def pk_data(ip, date1, date2):
    date_1 = int(time.mktime(date1.timetuple())*1000)
    date_2 = int(time.mktime(date2.timetuple())*1000)
    params = (
        ('returi', 'http://{}/report'.format(ip)),
    )
    data = {
        'redirect': 'http://{}/report'.format(ip),
        **dotenv_values(".env.pkpvd"),
        'commit': '\u0412\u043E\u0439\u0442\u0438'
    }
    session = requests.Session()
    session.post('http://{}/api/rs/login'.format(ip), params=params, data=data, verify=False)
    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
    }
    data = {
        "file": "Перечень документов из обращений.jrd",
        "output": "xlsx",
        "params": [
            {
            "name": "START_DATE",
            "label": "Начало периода",
            "type": "DATE",
            "required": "true",
            "value": date_1
            },
            {
            "name": "END_DATE",
            "label": "Конец периода",
            "type": "DATE",
            "required": "true",
            "value": date_2
            }
        ]
    }
    data_to_send = json.dumps(data).encode("utf-8")
    response1 = session.post(
        'http://{}/api/rs/reports/execute'.format(ip), 
        headers=headers, 
        data=data_to_send, 
        verify=False
    )
    with BytesIO(response1.content) as fh:
        df = pd.io.excel.read_excel(fh, usecols = 'C,I:L', skiprows = 3, header = 0, engine='openpyxl')
    if not df.empty:
        df['Дата'] = date_1
        df['Итого листов (подлинников)'] = df['Кол-во экз. документа']*df['Кол-во листов в подлиннике']
        df['Итого листов (копии)'] = df['Кол-во экз. копии документа']*df['Кол-во листов в копии']
    return df

# a function that return an .xlsx-file with an information about number of sheets used in all branches from a PKPVD program
def pk_sheet(request):
    if request.method == 'GET':
        date_form = DateFormAppointment
        return render(request, 'sheets_pk.html', 
                      {'date_form': date_form})
    if request.method == 'POST':
        form = DateFormAppointment(request.POST)
        if form.is_valid():
            date_begin = form.cleaned_data['date1_field']
            date_end = form.cleaned_data['date2_field']
        z = (date_end - date_begin).days + 1
        date_1 = str(time.mktime(date_begin.timetuple())*1000)
        date_2 = str(time.mktime(date_end.timetuple())*1000)
        engine = create_engine('postgresql{}'.format(os.getenv("DATABASE_URL")[4:]))
        query = readSqlScript('pksheet')
        query = query.replace('date_1', date_1).replace('date_2', date_2)
        df = pd.read_sql(query, con=engine)
#        df_itog = pd.DataFrame(
#            columns=[
#                'Наименование организации', 
#                'Кол-во экз. документа',
#                'Кол-во листов в подлиннике', 
#                'Кол-во экз. копии документа',
#                'Кол-во листов в копии', 
#                'Итого листов (подлинников)',
#                'Итого листов (копии)'
#            ]
#        )
#        for i in range(z):
#            date1 = (date_begin + timedelta(i))
#            data_1 = pk_data(os.getenv("PKIP1"), date1, date1)
#            data_2 = pk_data(os.getenv("PKIP2"), date1, date1)
#            data = pd.concat([data_1, data_2])
#            df_itog = df_itog.append(data)
        sio = BytesIO()
#        df_itog = df_itog.groupby(['Наименование организации']).sum()
        pd.io.formats.excel.ExcelFormatter.header_style = None
        PandasWriter = pd.ExcelWriter(sio, engine='xlsxwriter')
        df.to_excel(PandasWriter, index=None)
        # Formats Excel sheet
        workbook = PandasWriter.book
        worksheet = PandasWriter.sheets['Sheet1']
        worksheet.set_column('A:A', 200)
        worksheet.set_column('B:E', 10)
        PandasWriter.save()
        sio.seek(0)
        workbook = sio.getvalue()
        return returnxls(workbook, 'sheets') 

# autorization to SPER (getting an access token)
def sper(params, get='get', datareq=None, lnk='tkmv_ajax.html'):
    session = requests.Session()
    link = '{}/227.html'.format(os.getenv("LINKSPER"))
    data = {
        "rememberme": "0",
        
        "cmdweblogin": "\u0412\u043E\u0439\u0442\u0438"
    }
    response1 = session.post(link, data=data)
    link = '{0}/{1}'.format(os.getenv("LINKSPER"), lnk)
    if get=='post':
        r2 = session.post(link, params=params, data=datareq)
    else:
        r2 = session.get(link, params=params)
    return r2

# returns an information about all classification services from SPER
def class_serv(request):
    params = (
        ('action', 'jgrid_main_service_list'),
        ('use', '0'),
        ('view', 'list'),
        ('oper', 'grid'),
        ('_search', 'false'),
        ('nd', '1632124566686'),
        ('rows', '3000'),
        ('page', '1'),
        ('sidx', 'id'),
        ('sord', 'desc'),
    )
    r2 = sper(params)
    ss = r2.text.split('</script>')
    rtext = json.loads(ss[-1])
    data = rtext['rows']
    df = pd.json_normalize(data)
    df = df[['id','title', 'service_level']]
    sio = BytesIO()
    pd.io.formats.excel.ExcelFormatter.header_style = None
    PandasWriter = pd.ExcelWriter(sio, engine='xlsxwriter')
    df.to_excel(PandasWriter, index=None)
    # Formats Excel sheet
    workbook = PandasWriter.book
    worksheet = PandasWriter.sheets['Sheet1']
    worksheet.set_column('A:A', 6)
    worksheet.set_column('B:B', 190)
    worksheet.set_column('C:C', 17)
    PandasWriter.save()
    sio.seek(0)
    workbook = sio.getvalue()
    return returnxls(workbook, 'sheets')

# returns an information about organizations that are in SPER
def ogv_with_st(request):
    params = (
        ('action', 'jgrid_tkmv_org_list'),
        ('level', '100'),
        ('view', ''),
        ('mode', ''),
        ('gr', ''),
        ('oper', 'grid'),
        ('_search', 'false'),
        ('nd', '1632403410951'),
        ('rows', '3000'),
        ('page', '1'),
        ('sidx', ''),
        ('sord', 'asc'),
    )
    r2 = sper(params)
    ss = r2.text.split('</script>')
    rtext = json.loads(ss[-1])
    data = rtext['rows']
    df = pd.json_normalize(data)
    df = df[['id','short_title', 'level']]
    params1 = (('action', 'save_ov'),)
    lst = []
    for indexes, rows in df.iterrows():
        dataxx = {
        'act': 'check_use',
        'id': rows['id']
        }
        info = sper(params1, 'post', datareq=dataxx)
        ss = info.text.split('</script>')
        rtext = json.loads(ss[-1])
        data_standart = rtext['message']
        soup = BeautifulSoup(data_standart, 'lxml')
        allInfo = soup.find_all('li')
        i = {'id':rows['id'], 'short_title':rows['short_title'], 'level':rows['level']}
        for data in allInfo:
            if data.text[:16]== 'как организация,':
                i['как организация, ответственная за предоставление услуги для регламентов'] = data.text[73:]
            elif data.text[:16]== 'как организация ':
                i['как организация, ответственная за выполнение этапа регламентов'] = data.text[64:]
            elif data.text[:5]== 'в НПА':
                i['в НПА'] = data.text[7:]
            elif data.text[:5]== 'в меж':
                i['в межведомственных запросах'] = data.text[29:]
            elif data.text[:5]== 'в ста':
                i['в стандартах'] = data.text[14:]
            elif data.text[:5]== 'в рег':
                i['в регламентах'] = data.text[15:]
            elif data.text[:5]== 'в кла':
                i['в классификационных подуслугах'] = data.text[32:]
            else:
                i['Другое'] = data.text
        lst.append(i)
    sio = BytesIO()
    pd.io.formats.excel.ExcelFormatter.header_style = None
    df = pd.DataFrame(lst)
    PandasWriter = pd.ExcelWriter(sio, engine='xlsxwriter')
    df.to_excel(PandasWriter, index=None)
    # Formats Excel sheet
    workbook = PandasWriter.book
    worksheet = PandasWriter.sheets['Sheet1']
    worksheet.set_column('A:A', 6)
    worksheet.set_column('B:B', 190)
    worksheet.set_column('C:C', 17)
    PandasWriter.save()
    sio.seek(0)
    workbook = sio.getvalue()
    return returnxls(workbook, 'standarts')

# returns an information about all complex services from SPER
def kz(request):
    params = (
        ('action', 'jqgrid_complex_subservices_list'),
        ('oper', 'grid'),
        ('_search', 'false'),
        ('nd', '1632464893772'),
        ('rows', '100'),
        ('page', '1'),
        ('sidx', 'id'),
        ('sord', 'desc'),
    )
    response = sper(params=params)
    txt = response.text.split('</script>')
    data = json.loads(txt[-1])['rows']
    df = pd.json_normalize(data)
    df = df[['id', 'le_title']]
    lst = []
    for index, row in df.iterrows():
        params = (
            ('action', 'complex_subservice_form'),
            ('id', row['id']),
        )
        response = sper(params=params)
        soup = BeautifulSoup(response.text, 'lxml')
        allUl = soup.findAll('li', {'class': 'standard-row'})
        for data in allUl:
            num = data.find_next('strong').text
            nme = data.find_next('span', {'class': 'standard-title'}).text
            lst.append({'id':row['id'], 'title': row['le_title'],'standard_num':num, 'name':nme})
    fd = pd.DataFrame(lst)
    sio = BytesIO()
    pd.io.formats.excel.ExcelFormatter.header_style = None
    PandasWriter = pd.ExcelWriter(sio, engine='xlsxwriter')
    fd.to_excel(PandasWriter, index=None)
    # Formats Excel sheet
    workbook = PandasWriter.book
    worksheet = PandasWriter.sheets['Sheet1']
    worksheet.set_column('A:A', 6)
    worksheet.set_column('B:B', 127)
    worksheet.set_column('C:C', 17)
    PandasWriter.save()
    sio.seek(0)
    workbook = sio.getvalue()
    return returnxls(workbook, 'complex')

# returns an information about all inter-host requests from SPER
def mvz(request):
    params = (
        ('action', 'jgrid_admin_tkmv_serv_list'),
        ('oper', 'grid'),
        ('_search', 'false'),
        ('nd', '1632476540959'),
        ('rows', '1500'),
        ('page', '1'),
        ('sidx', ''),
        ('sord', 'asc'),
    )
    response = sper(params=params)
    txt = response.text.split('</script>')
    data = json.loads(txt[-1])['rows']
    df = pd.json_normalize(data)
    df = df[['id', 'title']]
    lst = []
    for index, row in df.iterrows():
        params = (
            ('type', 'serv'),
            ('id', row['id']),
        )
        response = sper(params=params, lnk='edit.html')
        soup = BeautifulSoup(response.text, 'lxml')
        stand = soup.select('tr[id*="standard"]')
        if len(stand) != 0:
            for i in stand:
                td = i.find_all('td')
                lst.append({
                    'id':row['id'], 
                    'name':row['title'],
                    'standard_id':td[0].text, 
                    'standard_name':td[1].text
                })
        else:
            lst.append({'id':row['id'], 'name':row['title']})
    fd = pd.DataFrame(lst)
    sio = BytesIO()
    pd.io.formats.excel.ExcelFormatter.header_style = None
    PandasWriter = pd.ExcelWriter(sio, engine='xlsxwriter')
    fd.to_excel(PandasWriter, index=None)
    # Formats Excel sheet
    workbook = PandasWriter.book
    worksheet = PandasWriter.sheets['Sheet1']
    worksheet.set_column('A:A', 6)
    worksheet.set_column('B:B', 127)
    worksheet.set_column('C:C', 17)
    PandasWriter.save()
    sio.seek(0)
    workbook = sio.getvalue()
    return returnxls(workbook, 'mvz')

# a function that returns an JSON response from SIER
def sier_adm_get(mainId):
    accessToken = sier()
    headers = {
    'Authorization': 'Bearer {}'.format(accessToken),
    'Content-Type': 'application/json',
    }
    params = (
        ('mainId', mainId),
    )
    response = requests.get(
        '{}/api/v1/find/settings'.format(os.getenv("LINK2")), 
        headers=headers, 
        params=params
    )
    return response

# a function that gets an information about codes of organizations in SIER
def sier_mejv_adm(request):
    r = sier_adm_get('5f3544b91099140ea41aec7e')
    data = json.loads(r.text)['value']
    df = pd.json_normalize(data)
    sio = BytesIO()
    PandasWriter = pd.ExcelWriter(sio, engine='xlsxwriter')
    df.to_excel(PandasWriter, index=None)
    # Formats Excel sheet
    workbook = PandasWriter.book
    worksheet = PandasWriter.sheets['Sheet1']
    worksheet.set_column('A:A', 6)
    worksheet.set_column('B:B', 127)
    worksheet.set_column('C:C', 17)
    PandasWriter.save()
    sio.seek(0)
    workbook = sio.getvalue()
    return returnxls(workbook, 'org_sier')

# a function that gets an information about codes of services in SIER
def sier_mejv_serv(request):
    r = sier_adm_get('5f3627961099140ea41aec81')
    data = json.loads(r.text)['value']
    df = pd.json_normalize(data)
    sio = BytesIO()
    PandasWriter = pd.ExcelWriter(sio, engine='xlsxwriter')
    df.to_excel(PandasWriter, index=None)
    # Formats Excel sheet
    workbook = PandasWriter.book
    worksheet = PandasWriter.sheets['Sheet1']
    worksheet.set_column('A:A', 26)
    worksheet.set_column('B:B', 127)
    worksheet.set_column('C:C', 17)
    PandasWriter.save()
    sio.seek(0)
    workbook = sio.getvalue()
    return returnxls(workbook, 'usl_sier')


# a function that gets an information all reglaments in SPER
def stend_sper(request):
    sio = BytesIO()
    pd.io.formats.excel.ExcelFormatter.header_style = None
    PandasWriter = pd.ExcelWriter(sio, engine='xlsxwriter')
    sper_edit(PandasWriter, '1', 'exported', 'СИЭР' )
    sper_edit(PandasWriter, '3', 'exported', 'Портал МФЦ')
    sper_edit(PandasWriter, '', 'stopped', 'Приостановленные')
    PandasWriter.save()
    sio.seek(0)
    workbook = sio.getvalue()
    return returnxls(workbook, 'stend_sper')

# returns an .xlsx sheet for stend_sper function
def sper_edit(Pdw, stend, typ, sh_name):
    params = (
        ('action', 'jgrid_el_reglament_list'),
        ('kind', 'all'),
        ('type', typ),
        ('stend', stend),
        ('office', ''),
        ('oper', 'grid'),
        ('_search', 'false'),
        ('nd', '1632723190260'),
        ('rows', '3000'),
        ('page', '1'),
        ('sidx', ''),
        ('sord', 'asc'),
    )
    stend_ais = sper(params)
    txt = stend_ais.text.split('</script>')
    rtext = json.loads(txt[-1])
    data = rtext['rows']
    df = pd.json_normalize(data)
    df = df[['id', 'title', 'last_modified', 'id_parent', 'mfc_kod', 'is_mfc', 'deleted', 'stopped']]
    df.to_excel(Pdw, index=None, sheet_name=sh_name)
    # Format Excels sheet
    workbook = Pdw.book
    worksheet = Pdw.sheets[sh_name]
    worksheet.set_column('A:A', 6)
    worksheet.set_column('B:B', 190)
    worksheet.set_column('C:C', 18)
    worksheet.set_column('E:E', 26)


def get_vals(page, pagess):
    data = {
        'type': 'getList',
        'sortBy': 'created',
        'sortDirection': 'desc',
        'title': '',
        'dateFrom': '',
        'dateTo': '',
        'pages': pagess,
        'page': page,
        'zone': 'fed',
        'displayTestRequests': 'false',
        'displayProdRequests': 'true'
    }
    response = requests.post(os.getenv('LINKSMEV'), data=data)
    soup = BeautifulSoup(response.text, 'lxml')
    return soup

# a function that returns a parsed data from SMEV3 techportal
def tech_port_smev(request):
    soupp = get_vals(1, 0)
    pages = int(soupp.find('script', {'type': 'text/javascript'}).string[6:9])
    df = pd.DataFrame(columns=range(0,7))
    for i in range(1, pages+1):
        soupp = get_vals(i, pages)
        ls = []
        for row in soupp.find_all('tr', limit=10):
            lst = []
            columns = row.find_all('td')
            for col in columns:
                lst.append(col.get_text())
            ls.append(lst)    
        df = df.append(pd.DataFrame(ls))
    sio = BytesIO()
    PandasWriter = pd.ExcelWriter(sio, engine='xlsxwriter')
    df.columns = [
        'Наименование', 
        'Назначение', 
        'Значение идентификатора', 
        'Область применения',
        'Версия',
        'Версия МР',
        'Дата регистрации'
    ]
    df.to_excel(PandasWriter, index=None)
    # Formats Excel sheet
    workbook = PandasWriter.book
    worksheet = PandasWriter.sheets['Sheet1']
    worksheet.set_column('A:A', 107)
    worksheet.set_column('B:B', 107)
    worksheet.set_column('C:C', 22)
    worksheet.set_column('D:D', 35)
    worksheet.set_column('E:F', 6)
    worksheet.set_column('G:G', 10)    
    PandasWriter.save()
    sio.seek(0)
    workbook = sio.getvalue()
    return returnxls(workbook, 'smev')


def get_token(link, sess):
    response = sess.get(link)
    soup = BeautifulSoup(response.text, 'lxml')
    token = soup.find('meta', {'name':'csrf-token'}).get('content')
    return token

# a function that returns a parsed data from IAS
def ias(request):
    session=requests.Session()
    data = {
        'authenticity_token':'',
        **dotenv_values(".env.ias"),
        'commit': '\u0410\u0432\u0442\u043E\u0440\u0438\u0437\u043E\u0432\u0430\u0442\u044C\u0441\u044F'
    }
    data['authenticity_token'] = get_token('{}/users/sign_in'.format(os.getenv('LINKIAS')), session)
    response = session.post('{}/users/sign_in'.format(os.getenv('LINKIAS')), data=data)
    response = session.get('{}/hershel/regions'.format(os.getenv('LINKIAS')))
    response = session.get('{}/hershel/regions/41'.format(os.getenv('LINKIAS'))) 
    token_services = get_token('{}/hershel/regions/41/reports/general'.format(os.getenv('LINKIAS')), session)
    sio = BytesIO()
    PandasWriter = pd.ExcelWriter(sio, engine='xlsxwriter')
    for i in ['federal', 'pprf', 'regional', 'municipal']:
        params = (
            ('report_type', 'quarter'),
            ('year', '2021'),
            ('quarter', '1'),
            ('month', '1'),
            ('date_start', ''),
            ('date_end', ''),
            ('category_ids[]', ['4', '5', '1', '2', '3']),
            ('mfc_ids[]', 'all'),
            ('service_type', i),
            ('service_ids[]', 'all'),
            ('_', '1632829078890'),
        )
        response = session.get(
            'https://vashkontrol.ru/hershel/regions/41/reports/general/services', 
            params=params, 
            headers = {
                'X-CSRF-Token':token_services, 
                'X-Requested-With':'XMLHttpRequest'
            }
        )
        soup = BeautifulSoup(response.text.replace('\\',''), 'lxml')
        lst = []
        data = soup.find_all('option')
        for val in data:
            lst.append(val.text.replace('n', ''))
        df = pd.DataFrame(lst[1:], columns = ['Наименование услуги'])
        df.to_excel(PandasWriter, index=None, sheet_name=i)
    PandasWriter.save()
    sio.seek(0)
    workbook = sio.getvalue()
    return returnxls(workbook, 'ias')

# a function that returns a parsed data from FRGU
def frgu(request):
    data = {
        'Услуги':os.getenv('LINKFRGU').replace('rzdl', 'report_generator_srv'),
        'Организации': os.getenv('LINKFRGU').replace('rzdl', 'report_generator_org'),
    }
    sio = BytesIO()
    pd.io.formats.excel.ExcelFormatter.header_style = None
    PandasWriter = pd.ExcelWriter(sio, engine='xlsxwriter')
    for key, value in data.items():
        response = requests.get(value)
        response.encoding=response.apparent_encoding
        soup = BeautifulSoup(response.text, 'lxml')
        table = soup.table(id='__bookmark_2')
        tr = table[0].find_all_next('tr')
        lst = []
        for i in tr:
            txt = i.text.strip().split('\n\n\n')
            if txt[0] in ['Региональный', 'Муниципальный']:
                txt.insert(0, '')
            lst.append(txt)
        df = pd.DataFrame(lst[1:], columns=lst[0])
        print(key, value)
        df.to_excel(PandasWriter, index=None, sheet_name=key)
        # Formats Excel sheet
        workbook = PandasWriter.book
        worksheet = PandasWriter.sheets[key]
        header_format = workbook.add_format()
        header_format.set_text_wrap()
        header_format.set_bold(True)
        worksheet.set_row(0, None, header_format)
        worksheet.set_column('A:A', 72)
        worksheet.set_column('B:B', 17)
        worksheet.set_column('C:C', 21)
        worksheet.set_column('D:D', 38)
        worksheet.set_column('E:E', 13)
        worksheet.set_column('F:F', 20)
        worksheet.set_column('G:G', 13)
        worksheet.set_column('H:H', 15)
    PandasWriter.save()
    sio.seek(0)
    workbook = sio.getvalue()
    return returnxls(workbook, 'frgu')

'''Data from SIER and Pentaho DB'''
# a data for MRS report
def mrs(request):
    if request.method == 'GET':
      date_form = DateFormMRS
      return render(request, 'mrs.html', {'date_form': date_form})
    if request.method == 'POST':
      form = DateFormMRS(request.POST)
      if form.is_valid():
          date_begin = form.cleaned_data['date1_field']
          date_end = form.cleaned_data['date2_field']
          if form.cleaned_data['urm_field'] == "2":
            urm = "NAME_MFC LIKE 'УРМ%' OR codeMFC = 21906"
          else:
            urm = "NAME_MFC NOT LIKE 'УРМ%' AND codeMFC <> 21906"
      date_begin_str = date_begin.strftime('%Y-%m-%d')
      date_end_str = date_end.strftime('%Y-%m-%d')
      cnxn = pymysql.connect(**dotenv_values(".env.base1"))
      cursor = cnxn.cursor()
      # select rows from SQL table to insert in dataframe.
      query = readSqlScript('mrs')
      query = query.replace('add_urm', urm).replace('date_1', date_begin_str).replace('date_2', date_end_str)
      # list of headers needed in query
      headb = ['Прием ФЛ', 'Прием ЮЛ', 'Выдача ФЛ', 'Выдача полож ФЛ',
                'Выдача ЮЛ', 'Выдача полож ЮЛ', 'Консультация']
      df = pd.read_sql(query, cnxn)
      # reset header style
      pd.io.formats.excel.ExcelFormatter.header_style = None
      # create a buffer for a table
      sz = BytesIO()
      PandasWriter = pd.ExcelWriter(sz, engine='xlsxwriter')
      for item in headb:
        df1 = pd.crosstab(
          [df['Код услуги'], df['Наименование услуги']], 
          [df['Код'], df['Наименование МФЦ']], 
          values=df[item],
          aggfunc='sum'
        )
        df1.to_excel(PandasWriter, sheet_name=item)
        # Format Excel sheet
        workbook = PandasWriter.book
        worksheet = PandasWriter.sheets[item]
        header_format = workbook.add_format()
        header_format.set_align('left')
        header_format.set_bold(False)
        row_format = workbook.add_format()
        row_format.set_align('center')
        row_format.set_bold(True)
        row_format1 = workbook.add_format()
        row_format1.set_text_wrap()
        row_format1.set_bold(True)
        worksheet.set_row(0, None, row_format)
        worksheet.set_row(1, None, row_format1)
        worksheet.set_column('B:B', 85, header_format)
        worksheet.set_column('C:AS', 23)

      PandasWriter.save()
      sz.seek(0)
      workbook = sz.getvalue()
      return returnxls(workbook, 'mrs')

# a function that gets users from SIER
def sier_users(request):
  cnxn = pymysql.connect(**dotenv_values(".env.base1"))
  cursor = cnxn.cursor()
  # select rows from SQL table to insert in dataframe.
  query = readSqlScript('users')
  # list of headers needed in query
  df = pd.read_sql(query, cnxn)
  df['active'] = df['active'].astype(bool)
  # reset header style
  pd.io.formats.excel.ExcelFormatter.header_style = None
  # create a buffer for a table
  sz = BytesIO()
  PandasWriter = pd.ExcelWriter(sz, engine='xlsxwriter')
  df.to_excel(PandasWriter, index=None)
  # Format Excel sheet
  workbook = PandasWriter.book
  worksheet = PandasWriter.sheets['Sheet1']
  worksheet.set_column('A:A', 15)
  worksheet.set_column('B:B', 45) 
  PandasWriter.save()
  sz.seek(0)
  workbook = sz.getvalue()
  return returnxls(workbook, 'users')

# a data for a committee
def otchet(request):
    if request.method == 'GET':
        date_form = DateFormAppointment
        return render(request, 'otchet.html', {'date_form': date_form})
    if request.method == 'POST':
        form = DateFormAppointment(request.POST)
        if form.is_valid():
            date_begin = form.cleaned_data['date1_field']
            date_end = form.cleaned_data['date2_field']
        date_begin_str = date_begin.strftime('%Y-%m-%d')
        date_end_str = date_end.strftime('%Y-%m-%d')
        cnxn = pymysql.connect(**dotenv_values(".env.base1"))
        cursor = cnxn.cursor()
        # select rows from SQL table to insert in dataframe.
        query = readSqlScript('fils')
        query = query.replace('date_1', date_begin_str).replace('date_2', date_end_str)
        df = pd.read_sql(query, cnxn)
        # reset header style
        pd.io.formats.excel.ExcelFormatter.header_style = None
        # create a buffer for a table
        sz = BytesIO()
        PandasWriter = pd.ExcelWriter(sz, engine='xlsxwriter')
        df.to_excel(PandasWriter, index=None)
        PandasWriter.save()
        sz.seek(0)
        workbook = sz.getvalue()
        return returnxls(workbook, 'otchet')

# another data for a committee
def add23(request):
    if request.method == 'GET':
        date_form = DateFormAppointment
        return render(request, 'add23.html', {'date_form': date_form})
    if request.method == 'POST':
        form = DateFormAppointment(request.POST)
        if form.is_valid():
            x = form.cleaned_data['date1_field']
            y = form.cleaned_data['date2_field']
        date_1 = x.strftime('%Y-%m-%d')
        date_2 = y.strftime('%Y-%m-%d')
        # connecting to MySQL DB
        cnxn = pymysql.connect(**dotenv_values(".env.base1"))
        cursor = cnxn.cursor()
        # select rows from SQL table to insert in dataframe.
        query = readSqlScript('23add')
        query = query.replace('date_1', date_1).replace('date_2', date_2)
        df = pd.read_sql(query, cnxn)
        headb = df['Наименование МФЦ'].unique()
        # reset header style
        pd.io.formats.excel.ExcelFormatter.header_style = None
        sz = BytesIO()
        PandasWriter = pd.ExcelWriter(sz, engine='xlsxwriter')
        # create a buffer for a table
        for item in headb:
            df1 = df[df['Наименование МФЦ']==item]
            if item[:6]=='Филиал':
                match = re.search(r'"[^"]*"', item[20:])
            elif item[:6] == 'Отдел ':
                match = re.search(r'"[^"]*"', item[6:])
            else:
                match = re.search(r'.*', item)
            df1.to_excel(PandasWriter, sheet_name=match[0].replace('"', ''), index=None)
        PandasWriter.save()
        sz.seek(0)
        workbook = sz.getvalue()
        return returnxls(workbook, 'add23')

'''Код для обработки данных присланного от ОК .xlsx-файла'''
def kadry(request):
    if request.method == 'GET':
        return render(request, 'kadry.html', {})
    if request.method == 'POST':
        excel_file = request.FILES['excel_file']
        # reading data from .xlsx-file sheets
        df_sheet1 = pd.read_excel(excel_file, sheet_name='Кадры (полный)', skiprows=2, header=0)
        df_sheet2 = pd.read_excel(excel_file, sheet_name='Кадры (реальность)', skiprows=1, header=0)
        df_sheet3 = pd.read_excel(excel_file, sheet_name='Кадры-отсутствия', skiprows=4, header=0)
        df_sheet4 = pd.read_excel(excel_file, sheet_name='Кадры-отсутствия (расчет)', header=0, index_col=0)
        df_sheet3["Вид отсутствия"] = df_sheet3["Вид отсутствия"].astype("category")
        df_sheet3["Вид отсутствия"].cat.set_categories(df_sheet4.columns, inplace=True)
        df_sheet3["Подразделение"] = df_sheet3["Подразделение"].astype("category")
        df_sheet3["Подразделение"].cat.set_categories(df_sheet4.index, inplace=True)
        # deleting the first row (because is has no data)
        df_sheet1 = df_sheet1.iloc[1:]
        df_sheet3 = df_sheet3.iloc[1:]

        df_sheet3 = df_sheet3.merge(df_sheet2, left_on='Сотрудник', right_on='ФИО (указывать вручную в соотвествии с 1С)', how='left')
        df_sheet3['Подразделение (итог)'] = df_sheet3['Прикомандирована (указывать вручную в соотвествии с 1С)'].fillna(df_sheet3['Подразделение'])
        df_sheet1 = df_sheet1.merge(df_sheet2, left_on='Сотрудник', right_on='ФИО (указывать вручную в соотвествии с 1С)', how='left')
        df_sheet1['Подразделение (итог)'] = df_sheet1['Прикомандирована (указывать вручную в соотвествии с 1С)'].fillna(df_sheet1['Подразделение'])
        df_sheet3 = df_sheet3[(df_sheet3['Должность'] == 'ведущий специалист')|
            (df_sheet3['Должность'] == 'главный специалист')]
        # Возраст
        df_sheet1.loc[
            df_sheet1['Возраст']<30, 
            'Возраст (сопоставление)'
            ] = 'До 30 лет'
        df_sheet1.loc[
            (df_sheet1['Возраст']>=30)&(df_sheet1['Возраст']<40), 
            'Возраст (сопоставление)'
            ] = '30-40'
        df_sheet1.loc[
            (df_sheet1['Возраст']>=40)&(df_sheet1['Возраст']<50), 
            'Возраст (сопоставление)'
            ] = '40-50'
        df_sheet1.loc[df_sheet1['Возраст']>=50, 
            'Возраст (сопоставление)'] = 'Старше 50'
        # Стаж работы на предприятии
        df_sheet1.loc[
            df_sheet1['Стаж работы на предприятии лет']<1, 
            'Стаж на предприятии (сопоставление)'
            ] = 'менее 1 года'
        df_sheet1.loc[
            (df_sheet1['Стаж работы на предприятии лет']>=1)&(df_sheet1['Стаж работы на предприятии лет']<3), 
            'Стаж на предприятии (сопоставление)'
            ] = '1-2 года'
        df_sheet1.loc[
            (df_sheet1['Стаж работы на предприятии лет']>=3)&(df_sheet1['Стаж работы на предприятии лет']<5), 
            'Стаж на предприятии (сопоставление)'
            ] = '3-5 лет'
        df_sheet1.loc[
            df_sheet1['Стаж работы на предприятии лет']>=5, 
            'Стаж на предприятии (сопоставление)'
            ] = 'более 5 лет'
        # Общий стаж работы
        df_sheet1.loc[
            df_sheet1['Общий стаж лет']<1, 
            'Общий стаж (сопоставление)'
            ] = ' менее 1 года'
        df_sheet1.loc[
            (df_sheet1['Общий стаж лет']>=1)&(df_sheet1['Общий стаж лет']<3), 
            'Общий стаж (сопоставление)'
            ] = ' 1-2 года'
        df_sheet1.loc[
            (df_sheet1['Общий стаж лет']>=3)&(df_sheet1['Общий стаж лет']<5), 
            'Общий стаж (сопоставление)'
            ] = ' 3-5 лет'
        df_sheet1.loc[
            df_sheet1['Общий стаж лет']>=5, 
            'Общий стаж (сопоставление)'
            ] = ' более 5 лет'

        df_sheet1["Возраст (сопоставление)"] = df_sheet1["Возраст (сопоставление)"].astype("category")
        df_sheet1["Возраст (сопоставление)"].cat.set_categories(['До 30 лет', '30-40', '40-50', 'Старше 50'], inplace=True)
        df = pd.crosstab(df_sheet3['Подразделение (итог)'], df_sheet3['Вид отсутствия'], dropna=False)
        df_sheet1['Состояние в браке'] = df_sheet1['Состояние в браке'].fillna('Состоит в незарегистрированном браке')
        ved_spec = pd.crosstab(df_sheet1['Подразделение (итог)'], df_sheet1['Должность'])
        ved_spec1 = pd.crosstab(df_sheet1['Подразделение (итог)'], df_sheet1['Возраст (сопоставление)'])
        ved_spec2 = pd.crosstab(df_sheet1['Подразделение (итог)'], df_sheet1['Состояние в браке'])
        ved_spec3 = pd.crosstab(df_sheet1['Подразделение (итог)'], df_sheet1['Пол'])
        ved_spec4 = pd.crosstab(df_sheet1['Подразделение (итог)'], df_sheet1['Стаж на предприятии (сопоставление)'])
        ved_spec5 = pd.crosstab(df_sheet1['Подразделение (итог)'], df_sheet1['Образование 1 вид образования'])
        ved_spec6 = pd.crosstab(df_sheet1['Подразделение (итог)'], df_sheet1['Общий стаж (сопоставление)'])
        df_it = ved_spec
        df_it['Возраст сотрудников']=''
        df_it = df_it.merge(ved_spec1, on='Подразделение (итог)')
        df_it['Семейное положение'] = ''
        df_it = df_it.merge(ved_spec2, on='Подразделение (итог)')
        df_it['Пол'] = ''
        df_it = df_it.merge(ved_spec3, on='Подразделение (итог)')
        df_it['Стаж работы в учреждении'] = ''
        df_it = df_it.merge(ved_spec4, on='Подразделение (итог)')
        df_it['Образование'] = ''
        df_it = df_it.merge(ved_spec5, on='Подразделение (итог)')
        df_it['Стаж работы общий'] = ''
        df_it = df_it.merge(ved_spec6, on='Подразделение (итог)')
        sio = BytesIO()
        PandasWriter = pd.ExcelWriter(sio, engine='xlsxwriter')
        df.to_excel(PandasWriter, sheet_name = 'Кадры-отсутствия (расчет)')
        df_it.to_excel(PandasWriter, sheet_name = 'Расчет (кадры)')
        df_sheet3.to_excel(PandasWriter, index=None, sheet_name = 'Кадры-отсутствия')
        df_sheet1.to_excel(PandasWriter, index=None, sheet_name = 'Кадры (полный)')
        PandasWriter.save()
        sio.seek(0)
        workbook = sio.getvalue()
        return returnxls(workbook, 'kadry')
