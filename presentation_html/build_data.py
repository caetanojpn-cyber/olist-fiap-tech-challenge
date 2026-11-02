from pathlib import Path
import csv, json
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'outputs'/'chart_data'
DST=ROOT/'presentation_html'/'chart_data.js'
FILES=['monthly_commercial_performance','orders_forecast_sep_dec_2018','semester_comparison','seller_pareto_curve','category_concentration','regional_distribution','logistics_stages','reviews_by_delivery_band','repeat_purchase_by_delivery','payment_mix','payment_installments','local_seller_logistics']
payload={}
for name in FILES:
    with (SRC/f'{name}.csv').open(encoding='utf-8-sig',newline='') as f:
        payload[name]=list(csv.DictReader(f))
DST.write_text('window.OLIST_DATA = '+json.dumps(payload,ensure_ascii=False)+';',encoding='utf-8')
print(f'Atualizado: {DST}')
