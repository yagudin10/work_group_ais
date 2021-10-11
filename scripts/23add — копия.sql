SELECT org.NAME_MFC AS 'Наименование МФЦ',
TB.title AS 'Уровень предоставления услуги (Категория услуги)',
sv.SERVICE_LEVEL,
'' AS 'Ведомство (Вышестоящая организация, которой подведомственно территориальное подразделение, оказывающее услугу)',
sv.SUBSERVICE_NAME AS 'Название услуги',
    SUM(IFNULL(TBL.priem_all, 0)+IFNULL(TBL.iss_all, 0)+IFNULL(TBL.iss_all_part, 0)+IFNULL(TBL.cons_all, 0)) AS 'Итого обращений',
    SUM(IFNULL(TBL.priem_fl, 0)) AS 'Всего принято Физ',
    SUM(IFNULL(TBL.iss_fl, 0)+IFNULL(TBL.iss_fl_part, 0)) AS 'Всего выдано Физ',
    SUM(IFNULL(TBL.iss_fl_pos, 0)) AS 'Всего выдано Физ в т.ч.пол.',
    SUM(IFNULL(TBL.cons_fl, 0)) AS 'Всего консультаций Физ',    
    SUM(IFNULL(TBL.priem_ul, 0)) AS 'Всего принято Юр',
    SUM(IFNULL(TBL.iss_ul, 0)+IFNULL(TBL.iss_ul_part, 0)) AS 'Всего выдано Юр',
    SUM(IFNULL(TBL.iss_ul_pos, 0)) AS 'Всего выдано Юр в т.ч.пол.',
    SUM(IFNULL(TBL.cons_ul, 0)) AS 'Всего консультаций Юр'
    FROM ais_service sv
LEFT JOIN sper_standart_type TB ON TB.id = sv.SERVICE_LEVEL
    CROSS JOIN (SELECT DISTINCT ID_MRS_MFC, codeMFC, NAME_MFC FROM serv_for_ais_mrs WHERE NAME_MFC NOT LIKE 'УРМ%' AND codeMFC NOT IN (22693, 21865, 21869)) org
    LEFT JOIN (SELECT ds.CLASSIFIC_SUBSERVICE_ID, 
        CASE WHEN ds.AFFILIATE_BRANCH_OID=22693 THEN 21903 ELSE ds.AFFILIATE_BRANCH_OID END AS AFFILIATE_BRANCH_OID,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 23 AND (ds.app_type_id in (0, 2) OR ds.app_type_id IS NULL) AND ds.CLASSIFIC_SUBSERVICE_ID NOT IN (852, 853, 854) THEN  CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS priem_fl,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 23 AND ds.app_type_id not in (0, 2) AND ds.CLASSIFIC_SUBSERVICE_ID NOT IN (852, 853, 854) THEN  CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS priem_ul,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 23 AND ds.CLASSIFIC_SUBSERVICE_ID NOT IN (852, 853, 854) THEN CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS priem_all,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 24 AND (ds.app_type_id in (0, 2) OR ds.app_type_id IS NULL) THEN CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS iss_fl,
		COUNT(DISTINCT(CASE WHEN ds.main_status_id = 24 AND (ds.app_type_id in (0, 2) OR ds.app_type_id IS NULL) AND ds.ANNUL_REASON IS NULL and  ds.STATUS_NAME<>'annulated' AND ds.RESULT_TYPE = 1
        THEN CONCAT(CASE WHEN ds.mainId IS NOT NULL  AND ds.SIER_DB_ID>0 THEN CONCAT(ds.mainId,'_') ELSE '' END,ds.DEAL_ID,'_',ds.INSTANCE_ID)  ELSE NULL END)) AS iss_fl_pos,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 24 AND ds.app_type_id not in (0, 2) THEN CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS iss_ul,
		COUNT(DISTINCT(CASE WHEN ds.main_status_id = 24 AND ds.app_type_id not in (0, 2) AND ds.ANNUL_REASON IS NULL and  ds.STATUS_NAME<>'annulated' AND ds.RESULT_TYPE = 1
        THEN CONCAT(CASE WHEN ds.mainId IS NOT NULL  AND ds.SIER_DB_ID>0 THEN CONCAT(ds.mainId,'_') ELSE '' END,ds.DEAL_ID,'_',ds.INSTANCE_ID) ELSE NULL END)) AS iss_ul_pos,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 24 THEN CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS iss_all, 
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 240 AND (ds.app_type_id in (0, 2) OR ds.app_type_id IS NULL) THEN ds.OBJECT_RID ELSE NULL END)) AS iss_fl_part,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 240 AND ds.app_type_id not in (0, 2) THEN ds.OBJECT_RID ELSE NULL END)) AS iss_ul_part,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 240 THEN ds.OBJECT_RID ELSE NULL END)) AS iss_all_part,
COUNT(DISTINCT CASE WHEN ds.main_status_id = 25 AND (ds.app_type_id in (0, 2) OR ds.app_type_id IS NULL) AND ds.CLASSIFIC_SUBSERVICE_ID NOT IN (852, 853, 854) THEN CONCAT(ds.mainId, '_', ds.CONSULT_ID) ELSE NULL END) AS cons_fl,
COUNT(DISTINCT CASE WHEN ds.main_status_id = 25 AND ds.app_type_id not in (0, 2) AND ds.CLASSIFIC_SUBSERVICE_ID NOT IN (852, 853, 854) THEN CONCAT(ds.mainId, '_', ds.CONSULT_ID) ELSE NULL END) AS cons_ul,
        COUNT(DISTINCT CASE WHEN ds.main_status_id = 25 AND ds.CLASSIFIC_SUBSERVICE_ID NOT IN (852, 853, 854) THEN CONCAT(ds.mainId, '_', ds.CONSULT_ID) ELSE NULL END) AS cons_all
        FROM deal_stats ds
        LEFT JOIN ais_sper_ogv ogv on ogv.SPER_OGV_ID = ds.SPER_OGV_ID
        LEFT JOIN sier_subservicescomplex cx on cx.id = ds.complexSubserviceId
        WHERE ds.event_day BETWEEN 'date_1' AND 'date_2'
            AND ds.main_status_id IN (23, 24, 240, 25)
            AND ds.CLASSIFIC_SUBSERVICE_ID NOT IN (818, 845, 846)
            AND ds.CLASSIFIC_SUBSERVICE_ID IS NOT NULL
            AND ds.ANNUL_REASON IS NULL
            AND ds.STATUS_NAME != 'annulated'
        GROUP BY ds.CLASSIFIC_SUBSERVICE_ID,
        ds.AFFILIATE_BRANCH_OID) TBL on sv.SUBSERVICE_ID=TBL.CLASSIFIC_SUBSERVICE_ID AND org.codeMFC = TBL.AFFILIATE_BRANCH_OID
    WHERE sv.SERVICE_LEVEL <>0
    AND sv.SUBSERVICE_ID NOT IN (818, 845, 846)
    GROUP BY TB.title, SUBSERVICE_NAME, sv.SERVICE_LEVEL, org.NAME_MFC
    ORDER BY NAME_MFC, sv.SERVICE_LEVEL