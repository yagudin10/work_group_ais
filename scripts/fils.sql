SELECT org.NAME_MFC AS 'Наименование МФЦ',
sv.SUBSERVICE_ID AS 'Код услуги',
sv.SUBSERVICE_NAME AS 'Наименование услуги',
    SUM(IFNULL(TBL.priem_all, 0)) AS 'Прием',
    SUM(IFNULL(TBL.iss_all, 0)+IFNULL(TBL.iss_all_part, 0)) AS 'Выдача',
    SUM(IFNULL(TBL.cons_all, 0)) AS 'Консультации',
    SUM(IFNULL(TBL.complex, 0)) AS 'В рамках комплексного запроса',
    SUM(IFNULL(TBL.zhs, 0)) AS 'В рамках жизненной ситуации',
    SUM(IFNULL(TBL.priem_ul, 0)+IFNULL(TBL.iss_ul, 0)+IFNULL(TBL.iss_ul_part, 0)+IFNULL(TBL.cons_ul, 0)) AS 'Юридическим лицам',
    SUM(IFNULL(TBL.priem_fl, 0)+IFNULL(TBL.iss_fl, 0)+IFNULL(TBL.iss_fl_part, 0)+IFNULL(TBL.cons_fl, 0)) AS 'Физическим лицам',
    'не учитываются' AS 'МСП',
    TB.title AS 'В разрезе уровня (государственные, муниципальные, иные)',
    SUM(IFNULL(TBL.otkaz, 0)) AS 'Количество отказов',
    SUM(IFNULL(TBL.vyd_mfc, 0)) AS 'Место получения результата - МФЦ',
    SUM(IFNULL(TBL.postamat, 0)) AS 'Место получения результата - Постамат (МФЦ)',
    SUM(IFNULL(TBL.vyd_ogv, 0)) AS 'Место получения результата - ОГВ',
    SUM(IFNULL(TBL.priost, 0)) AS 'Количество приостановок'
    FROM ais_service sv
LEFT JOIN sper_standart_type TB ON TB.id = sv.SERVICE_LEVEL
    CROSS JOIN (SELECT DISTINCT ID_MRS_MFC, codeMFC, NAME_MFC FROM serv_for_ais_mrs) org
    LEFT JOIN (SELECT ds.CLASSIFIC_SUBSERVICE_ID, 
        ds.AFFILIATE_BRANCH_OID,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 23 AND (ds.app_type_id in (0, 2) OR ds.app_type_id IS NULL) THEN  CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS priem_fl,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 23 AND ds.app_type_id not in (0, 2) THEN  CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS priem_ul,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 23 THEN CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS priem_all,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 24 AND (ds.app_type_id in (0, 2) OR ds.app_type_id IS NULL) THEN CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS iss_fl,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 24 AND ds.app_type_id not in (0, 2) THEN CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS iss_ul,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 24 THEN CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS iss_all, 
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 240 AND (ds.app_type_id in (0, 2) OR ds.app_type_id IS NULL) THEN ds.OBJECT_RID ELSE NULL END)) AS iss_fl_part,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 240 AND ds.app_type_id not in (0, 2) THEN ds.OBJECT_RID ELSE NULL END)) AS iss_ul_part,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 240 THEN ds.OBJECT_RID ELSE NULL END)) AS iss_all_part,
COUNT(DISTINCT CASE WHEN ds.main_status_id = 25 AND (ds.app_type_id in (0, 2) OR ds.app_type_id IS NULL) THEN CONCAT(ds.mainId, '_', ds.CONSULT_ID) ELSE NULL END) AS cons_fl,
COUNT(DISTINCT CASE WHEN ds.main_status_id = 25 AND ds.app_type_id not in (0, 2) THEN CONCAT(ds.mainId, '_', ds.CONSULT_ID) ELSE NULL END) AS cons_ul,
        COUNT(DISTINCT CASE WHEN ds.main_status_id = 25 THEN CONCAT(ds.mainId, '_', ds.CONSULT_ID) ELSE NULL END) AS cons_all,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 23 AND ds.isComplex=1 THEN CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS complex,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 23 AND (cx.title LIKE 'Жизненная ситуация%') THEN CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS zhs,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id IN (25,32) AND resultType='negative' THEN CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS otkaz,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 24 AND issueType='personally' THEN CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS vyd_mfc,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 24 AND issueType='postamat' THEN CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS postamat,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 33 THEN CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS vyd_ogv,
        COUNT(DISTINCT(CASE WHEN ds.main_status_id = 24 AND resultType='paused' THEN CONCAT(ds.mainId, '_', ds.DEAL_ID) ELSE NULL END)) AS priost
        FROM deal_stats ds
        LEFT JOIN ais_sper_ogv ogv on ogv.SPER_OGV_ID = ds.SPER_OGV_ID
        LEFT JOIN sier_subservicescomplex cx on cx.id = ds.complexSubserviceId
        WHERE ds.event_day BETWEEN 'date_1' AND 'date_2'
            AND ds.main_status_id IN (23, 24, 240, 25, 32, 33)
            AND ds.CLASSIFIC_SUBSERVICE_ID IS NOT NULL
            AND ds.ANNUL_REASON IS NULL
            AND ds.STATUS_NAME != 'annulated'
        GROUP BY ds.CLASSIFIC_SUBSERVICE_ID,
        ds.AFFILIATE_BRANCH_OID) TBL on sv.SUBSERVICE_ID=TBL.CLASSIFIC_SUBSERVICE_ID AND org.codeMFC = TBL.AFFILIATE_BRANCH_OID
    WHERE sv.SERVICE_LEVEL <>0
    AND sv.SERVICE_LEVEL <>6
    GROUP BY TB.title, SUBSERVICE_NAME, SUBSERVICE_ID, org.ID_MRS_MFC, NAME_MFC
    ORDER BY NAME_MFC