SELECT "Наименование организации", 
SUM(doc_orig) AS "Кол-во экз. документа", 
SUM(doc_orig_total) AS "Кол-во листов в подлиннике", 
SUM(doc_copies) AS "Кол-во экз. копии документа", 
SUM(doc_copies_total) AS "Кол-во листов в копии", 
SUM(doc_orig_total_sheets) AS "Итого листов (подлинников)", 
SUM(doc_copies_total_sheets) AS "Итого листов (копии)" 
FROM pk_sheets 
WHERE 
"Дата" BETWEEN date_1 AND date_2
GROUP BY "Наименование организации"
