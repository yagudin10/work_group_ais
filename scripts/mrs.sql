SELECT TB.external_id AS 'Код услуги', sv.SUBSERVICE_NAME AS 'Наименование услуги',
    org.ID_MRS_MFC AS 'Код', org.NAME_MFC AS 'Наименование МФЦ',
    SUM(IFNULL(TBL.priem_fl, 0)) AS 'Прием ФЛ',
    SUM(IFNULL(TBL.priem_ul, 0)) AS 'Прием ЮЛ',
    SUM(IFNULL(TBL.iss_fl, 0)+IFNULL(TBL.iss_fl_part, 0)) AS 'Выдача ФЛ',
    SUM(IFNULL(TBL.iss_fl_pos, 0)) AS 'Выдача полож ФЛ',
    SUM(IFNULL(TBL.iss_ul, 0)+IFNULL(TBL.iss_ul_part, 0)) AS 'Выдача ЮЛ',
    SUM(IFNULL(TBL.iss_ul_pos, 0)) AS 'Выдача полож ЮЛ',
    SUM(IFNULL(TBL.cons_all, 0)) AS 'Консультация'
    FROM ais_service sv
LEFT JOIN (SELECT DISTINCT mrs.external_id, ss.classificSubserviceId FROM dwh.serv_for_ais_mrs mrs
LEFT JOIN sier_subservices ss ON ss._id = mrs.subservId) TB ON TB.classificSubserviceId = sv.SUBSERVICE_ID
    CROSS JOIN (SELECT DISTINCT ID_MRS_MFC, codeMFC, NAME_MFC FROM serv_for_ais_mrs WHERE add_urm) org
    LEFT JOIN (SELECT ds.CLASSIFIC_SUBSERVICE_ID,
        (CASE WHEN ds.AFFILIATE_BRANCH_OID=22693 THEN 21903 ELSE ds.AFFILIATE_BRANCH_OID END) AS AFFILIATE_BRANCH_OID,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 23 AND (ds.app_type_id in (0, 2) OR ds.app_type_id IS NULL) THEN  CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS priem_fl,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 23 AND ds.app_type_id not in (0, 2) THEN  CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS priem_ul,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 23 THEN CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS priem_all,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 24 AND (ds.app_type_id in (0, 2) OR ds.app_type_id IS NULL) THEN CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS iss_fl,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 24 AND (ds.app_type_id in (0, 2) OR ds.app_type_id IS NULL) AND ds.ANNUL_REASON IS NULL and  ds.STATUS_NAME<>'annulated' AND ds.RESULT_TYPE = 1
        THEN CONCAT(CASE WHEN ds.mainId IS NOT NULL  AND ds.SIER_DB_ID>0 THEN CONCAT(ds.mainId,'_') ELSE '' END,ds.DEAL_ID,'_',ds.INSTANCE_ID)  ELSE NULL END)) AS iss_fl_pos,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 24 AND ds.app_type_id not in (0, 2) THEN CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS iss_ul,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 24 AND ds.app_type_id in (1, 3, 4, 5, 6, 7) AND ds.ANNUL_REASON IS NULL and  ds.STATUS_NAME<>'annulated' AND ds.RESULT_TYPE = 1
        THEN CONCAT(CASE WHEN ds.mainId IS NOT NULL  AND ds.SIER_DB_ID>0 THEN CONCAT(ds.mainId,'_') ELSE '' END,ds.DEAL_ID,'_',ds.INSTANCE_ID)  ELSE NULL END)) AS iss_ul_pos,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 24 THEN CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS iss_all, 
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 240 AND (ds.app_type_id in (0, 2) OR ds.app_type_id IS NULL) THEN ds.OBJECT_RID ELSE NULL END)) AS iss_fl_part,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 240 AND (ds.app_type_id in (0, 2) OR ds.app_type_id IS NULL) AND ds.resultType = 'positive' THEN ds.OBJECT_RID ELSE NULL END)) AS iss_fl_pos_part,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 240 AND ds.app_type_id not in (0, 2) THEN ds.OBJECT_RID ELSE NULL END)) AS iss_ul_part,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 240 AND ds.app_type_id not in (0, 2) AND ds.resultType = 'positive' THEN ds.OBJECT_RID ELSE NULL END)) AS iss_ul_pos_part,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 240 THEN ds.OBJECT_RID ELSE NULL END)) AS iss_all_part,
        COUNT(DISTINCT CASE WHEN ds.main_status_id = 25 AND (ds.app_type_id in (0, 2) OR ds.app_type_id IS NULL) THEN CONCAT(ds.mainId, '_', ds.CONSULT_ID) ELSE NULL END) AS cons_fl,
        COUNT(DISTINCT CASE WHEN ds.main_status_id = 25 AND ds.app_type_id not in (0, 2) THEN CONCAT(ds.mainId, '_', ds.CONSULT_ID) ELSE NULL END) AS cons_ul,
        COUNT(DISTINCT CASE WHEN ds.main_status_id = 25 THEN CONCAT(ds.mainId, '_', ds.CONSULT_ID) ELSE NULL END) AS cons_all
        FROM deal_stats ds
        LEFT JOIN ais_sper_ogv ogv on ogv.SPER_OGV_ID = ds.SPER_OGV_ID
        WHERE ds.event_day BETWEEN 'date_1' AND 'date_2'
            AND ds.main_status_id IN (23, 24, 240, 25)
            AND ds.CLASSIFIC_SUBSERVICE_ID IS NOT NULL
            AND ds.ANNUL_REASON IS NULL
            AND ds.STATUS_NAME != 'annulated'
        GROUP BY ds.CLASSIFIC_SUBSERVICE_ID,
        ds.AFFILIATE_BRANCH_OID) TBL on sv.SUBSERVICE_ID=TBL.CLASSIFIC_SUBSERVICE_ID AND org.codeMFC = TBL.AFFILIATE_BRANCH_OID
    WHERE sv.SERVICE_LEVEL <>0
    GROUP BY SUBSERVICE_NAME, org.ID_MRS_MFC, NAME_MFC, external_id
    ORDER BY NAME_MFC