SELECT vt.ticket_id as 'Номер талона'
            ,serv.rpt_name as 'Услуга'
            ,q.rpt_name as 'Очередь'
            ,FORMAT(ev.create_timestamp, 'HH:mm') as 'Взятие талона'
            ,FORMAT(ev.call_timestamp, 'HH:mm') as 'Вызов талона'
            ,CONVERT(varchar, DATEADD(s, ev.time_key + ev.waiting_time + ev.transaction_time, 0), 108) as 'Обслужен'
            ,CONVERT(varchar, DATEADD(s, ev.waiting_time, 0), 108) as 'Время ожидания'
            ,CONVERT(varchar, DATEADD(s, ev.transaction_time, 0), 108) as 'Время обслуживания'
            ,CONCAT(staff.rpt_first_name, ' ', staff.rpt_last_name) as 'Сотрудник'
            ,sp.name as 'Окно'
            ,ap.customer_id 'ID клиента'
        FROM [stat].[fact_visit_transaction] ev
        left join stat.dim_visit vt on vt.id = ev.visit_key
        left join stat.dim_branch bch on bch.id = ev.branch_key
        left join stat.dim_service serv on serv.id = ev.service_key
        left join stat.dim_queue q on q.id = ev.queue_key
        left join stat.dim_staff staff on staff.id = ev.staff_key
        left join stat.dim_service_point sp on sp.id = ev.service_point_key
        left join stat.fact_appointment ap on ap.origin_id = ev.appointment_id
        where ev.date_key = '{}'
        and bch.rpt_name ='{}'
        order by ev.time_key + ev.transaction_time