from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("nearest_appointment_date/", views.nearest_appointment_date, name="nearest_appointment_date"),
    path("talon/", views.talon, name="talon"),
    path("app/", views.create_table, name="app"),
    path("adm/", views.ros_administ, name="adm"),
    path("class_serv/", views.class_serv, name="class_serv"),
    path("ogv_with_st/", views.ogv_with_st, name="ogv_with_st"),
    path("kz/", views.kz, name="kz"),
    path("mvz/", views.mvz, name="mvz"),
    path("sier_mejv_adm/", views.sier_mejv_adm, name="sier_mejv_adm"),
    path("sier_mejv_serv/", views.sier_mejv_serv, name="sier_mejv_serv"),
    path("stend_sper/", views.stend_sper, name="stend_sper"),
    path("sved_smev/", views.tech_port_smev, name="tech_port_smev"),
    path("ias/", views.ias, name="ias"),
    path("kadry/", views.kadry, name="kadry"),
    path("frgu/", views.frgu, name="frgu"),
    path("mrs/", views.mrs, name="mrs"),
    path("otchet/", views.otchet, name="otchet"),
    path("sier_users/", views.sier_users, name="sier_users"),
    path("add23/", views.add23, name="add23"),
    path("sheetspk/", views.pk_sheet, name="pk"),

    path("test/", views.test),
]