#!/usr/bin/env python3
"""Reproducible analysis of the Olist Brazilian E-Commerce dataset.

Run from the repository root: python src/analysis.py
Outputs are written to outputs/. Monetary values are BRL.
"""
from pathlib import Path
import json
import warnings
import numpy as np
import pandas as pd
from scipy.stats import fisher_exact
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)
CHART = OUT / "chart_data"
CHART.mkdir(exist_ok=True)

FILES = {
    "orders": "olist_orders_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "geo": "olist_geolocation_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "translation": "product_category_name_translation.csv",
}

def load_data():
    missing = [f for f in FILES.values() if not (DATA / f).exists()]
    if missing:
        raise FileNotFoundError("Arquivos ausentes em data/: " + ", ".join(missing))
    d = {k: pd.read_csv(DATA / v) for k, v in FILES.items()}
    date_cols = [c for c in d["orders"].columns if c.endswith("_timestamp") or c.endswith("_date")]
    for c in date_cols + ["order_approved_at"]:
        if c in d["orders"]:
            d["orders"][c] = pd.to_datetime(d["orders"][c], errors="coerce")
    for c in ["review_creation_date", "review_answer_timestamp"]:
        if c in d["reviews"]:
            d["reviews"][c] = pd.to_datetime(d["reviews"][c], errors="coerce")
    return d

def save_csv(df, name):
    df.to_csv(OUT / name, index=False, encoding="utf-8-sig")

def save_chart(df, name):
    df.to_csv(CHART / name, index=False, encoding="utf-8-sig")

def money(x):
    return round(float(x), 2) if pd.notna(x) else None

def main():
    d = load_data()
    orders, items = d["orders"].copy(), d["items"].copy()
    customers, sellers = d["customers"], d["sellers"]
    reviews, payments = d["reviews"].copy(), d["payments"].copy()

    # Scope: valid purchase timestamps in the main observed period (Jan/2017-Aug/2018).
    start, end = pd.Timestamp("2017-01-01"), pd.Timestamp("2018-09-01")
    o = orders[orders.order_purchase_timestamp.ge(start) & orders.order_purchase_timestamp.lt(end)].copy()
    oi = items.merge(o[["order_id", "customer_id", "order_purchase_timestamp", "order_status",
                        "order_delivered_customer_date", "order_estimated_delivery_date",
                        "order_delivered_carrier_date", "order_approved_at"]], on="order_id", how="inner")
    oi["gross_value"] = oi["price"].fillna(0) + oi["freight_value"].fillna(0)

    # Commercial performance, monthly and semester comparison.
    order_product = oi.groupby("order_id").agg(product_value=("price", "sum"), gmv=("gross_value", "sum"))
    o = o.merge(order_product, left_on="order_id", right_index=True, how="left")
    o["month"] = o.order_purchase_timestamp.dt.to_period("M").astype(str)
    monthly = o.groupby("month").agg(orders=("order_id", "nunique"), gmv=("gmv", "sum"),
                                      avg_product_ticket=("product_value", "mean")).reset_index()
    monthly["month_label"] = pd.to_datetime(monthly.month + "-01").dt.strftime("%m/%y")
    save_csv(monthly, "monthly_commercial_performance.csv")
    save_chart(monthly, "monthly_commercial_performance.csv")
    sem = o[o.order_purchase_timestamp.dt.year.isin([2017, 2018]) & (o.order_purchase_timestamp.dt.month <= 6)].copy()
    sem["semester"] = sem.order_purchase_timestamp.dt.year.astype(str) + "_1S"
    semester = sem.groupby("semester").agg(orders=("order_id", "nunique"), gmv=("gmv", "sum"),
                                              avg_product_ticket=("product_value", "mean")).reset_index()
    save_csv(semester, "semester_comparison.csv")
    save_chart(semester, "semester_comparison.csv")

    # Delivery punctuality and review relationship.
    delivered = o[o.order_status.eq("delivered") & o.order_delivered_customer_date.notna()].copy()
    delivered["lead_days"] = (delivered.order_delivered_customer_date - delivered.order_purchase_timestamp).dt.total_seconds()/86400
    delivered["late"] = delivered.order_delivered_customer_date > delivered.order_estimated_delivery_date
    delivered["on_time"] = ~delivered["late"]
    reviews = reviews.sort_values("review_creation_date").drop_duplicates("order_id", keep="first")
    rv = delivered[["order_id", "lead_days", "late", "on_time"]].merge(reviews[["order_id", "review_score"]], on="order_id", how="inner")
    review_summary = rv.groupby("late").agg(n=("order_id", "nunique"), avg_score=("review_score", "mean"),
                                               one_star_rate=("review_score", lambda x: (x == 1).mean())).reset_index()
    review_summary["late"] = review_summary["late"].map({False: "on_time", True: "late"})
    save_csv(review_summary, "reviews_by_delivery_status.csv")
    rv["lead_time_band"] = pd.cut(rv.lead_days, bins=[-np.inf,5,10,15,20,30,np.inf], labels=["0 a 5","5 a 10","10 a 15","15 a 20","20 a 30","30+"])
    review_bands = rv.groupby(["lead_time_band","late"], observed=False).agg(n=("order_id","nunique"), avg_review_score=("review_score","mean"), one_star_rate=("review_score",lambda x:(x==1).mean())).reset_index()
    review_bands["delivery_status"] = review_bands.late.map({False:"Entregue no prazo",True:"Entregue com atraso"})
    save_chart(review_bands, "reviews_by_delivery_band.csv")
    save_chart(review_summary.rename(columns={"avg_score":"avg_review_score"}), "reviews_by_delivery_status.csv")

    # Seller concentration based on GMV from delivered items only.
    delivered_ids = set(delivered.order_id)
    seller_gmv = oi[oi.order_id.isin(delivered_ids)].groupby("seller_id").gross_value.sum().sort_values(ascending=False)
    seller_gmv = seller_gmv[seller_gmv > 0]
    n_s = len(seller_gmv)
    concentration = {"eligible_sellers": int(n_s),
        "top_1pct_gmv_share": float(seller_gmv.head(max(1, int(np.ceil(n_s*.01)))).sum()/seller_gmv.sum()),
        "top_10pct_gmv_share": float(seller_gmv.head(max(1, int(np.ceil(n_s*.10)))).sum()/seller_gmv.sum())}
    cat = oi[oi.order_id.isin(delivered_ids)].merge(d["products"][["product_id", "product_category_name"]], on="product_id", how="left")
    cat = cat[cat.product_category_name.notna()].groupby("product_category_name").gross_value.sum().sort_values(ascending=False)
    concentration["top_10_categories_gmv_share"] = float(cat.head(10).sum()/cat.sum()) if cat.sum() else None
    seller_table = seller_gmv.rename("delivered_gmv_brl").reset_index()
    seller_table["seller_rank"] = np.arange(1, len(seller_table)+1)
    seller_table["seller_share_pct"] = seller_table.delivered_gmv_brl / seller_table.delivered_gmv_brl.sum() * 100
    seller_table["cumulative_gmv_pct"] = seller_table.seller_share_pct.cumsum()
    seller_table["cumulative_seller_pct"] = seller_table.seller_rank / len(seller_table) * 100
    save_csv(seller_table, "seller_concentration.csv")
    save_chart(seller_table, "seller_concentration.csv")
    pareto_rows=[]
    for pct in [1,5,10,20,40,60,80,100]:
        n=int(np.ceil(len(seller_table)*pct/100))
        pareto_rows.append({"seller_percent":pct,"gmv_cumulative_pct":seller_table.head(n).delivered_gmv_brl.sum()/seller_table.delivered_gmv_brl.sum()*100,"uniform_reference_pct":pct,"seller_count":n})
    save_chart(pd.DataFrame(pareto_rows), "seller_pareto_curve.csv")
    cat_table=cat.rename("delivered_gmv_brl").head(10).reset_index()
    cat_table["gmv_share_pct"] = cat_table.delivered_gmv_brl / cat.sum() * 100
    cat_table=cat_table.rename(columns={"product_category_name":"category_label"})
    save_chart(cat_table, "category_concentration.csv")

    # Customer repeat cohort: first delivered order purchased Jan-Aug 2017; repeat by purchase date within 365 days.
    cust_orders = delivered.merge(customers[["customer_id", "customer_unique_id"]], on="customer_id", how="left")
    cust_orders = cust_orders.sort_values("order_purchase_timestamp")
    first = cust_orders[cust_orders.order_purchase_timestamp.lt("2017-09-01")].groupby("customer_unique_id").first().reset_index()
    first = first[first.order_purchase_timestamp.ge("2017-01-01")]
    purchase_dates_by_customer = cust_orders.groupby("customer_unique_id")["order_purchase_timestamp"].agg(list).to_dict()
    first["repeat_365d"] = [
        any(r.order_purchase_timestamp < dt <= r.order_purchase_timestamp + pd.Timedelta(days=365)
            for dt in purchase_dates_by_customer.get(r.customer_unique_id, []))
        for r in first[["customer_unique_id", "order_purchase_timestamp"]].itertuples(index=False)
    ]
    tab = pd.crosstab(first["late"], first["repeat_365d"]).reindex(index=[False, True], columns=[False, True], fill_value=0)
    _, repeat_p = fisher_exact(tab.values)
    repeat = first.groupby("late").agg(
        customers=("customer_unique_id", "nunique"),
        repeat_rate=("repeat_365d", "mean"),
        repeat_customers=("repeat_365d", "sum")
    ).reset_index()
    repeat["delivery_status"] = repeat["late"].map({False:"on_time", True:"late"})
    save_csv(repeat, "repeat_purchase_by_delivery.csv")
    save_chart(repeat, "repeat_purchase_by_delivery.csv")

    # Sensibilidade metodológica: define a coorte pela primeira entrega ocorrida entre jan-ago/2017
    # e conta uma segunda entrega nos 365 dias seguintes à primeira entrega.
    delivered_sorted = cust_orders.dropna(subset=["order_delivered_customer_date"]).sort_values("order_delivered_customer_date")
    first_by_delivery = delivered_sorted.groupby("customer_unique_id").first().reset_index()
    first_by_delivery = first_by_delivery[
        first_by_delivery.order_delivered_customer_date.ge("2017-01-01")
        & first_by_delivery.order_delivered_customer_date.lt("2017-09-01")
    ].copy()
    delivered_dates_by_customer = delivered_sorted.groupby("customer_unique_id")["order_delivered_customer_date"].agg(list).to_dict()
    first_by_delivery["repeat_365d_from_delivery"] = [
        any(r.order_delivered_customer_date < dt <= r.order_delivered_customer_date + pd.Timedelta(days=365)
            for dt in delivered_dates_by_customer.get(r.customer_unique_id, []))
        for r in first_by_delivery[["customer_unique_id", "order_delivered_customer_date"]].itertuples(index=False)
    ]
    sensitivity_tab = pd.crosstab(first_by_delivery["late"], first_by_delivery["repeat_365d_from_delivery"]).reindex(index=[False, True], columns=[False, True], fill_value=0)
    _, repeat_delivery_p = fisher_exact(sensitivity_tab.values)
    repeat_delivery_sensitivity = first_by_delivery.groupby("late").agg(
        customers=("customer_unique_id", "nunique"),
        repeat_rate=("repeat_365d_from_delivery", "mean"),
        repeat_customers=("repeat_365d_from_delivery", "sum")
    ).reset_index()
    save_csv(repeat_delivery_sensitivity, "repeat_purchase_delivery_date_sensitivity.csv")

    # Payment mix.
    p = payments.merge(o[["order_id"]], on="order_id", how="inner")
    pay_mix = p.groupby("payment_type").payment_value.sum().sort_values(ascending=False)
    pay_mix = pay_mix[pay_mix > 0]  # remove categorias sem valor financeiro do gráfico e dos indicadores
    pay_mix_df=pay_mix.rename("payment_value_brl").reset_index()
    pay_mix_df["share_paid_value_pct"] = pay_mix_df.payment_value_brl / pay_mix_df.payment_value_brl.sum() * 100
    save_csv(pay_mix_df, "payment_mix.csv")
    save_chart(pay_mix_df, "payment_mix.csv")
    cc = p[p.payment_type.eq("credit_card")]
    cc_order_installments = cc.groupby("order_id").payment_installments.max()
    cc_order_value = cc.groupby("order_id").payment_value.sum().rename("order_value_brl")
    pay_orders = pd.concat([cc_order_installments.rename("installments"),cc_order_value],axis=1).dropna()
    pay_orders["installment_band"] = pd.cut(pay_orders.installments, bins=[0,1,3,6,10,np.inf], labels=["1x","2–3x","4–6x","7–10x","11x+"])
    pay_inst = pay_orders.groupby("installment_band", observed=False).agg(orders=("order_value_brl","size"),median_order_value_brl=("order_value_brl","median")).reset_index()
    save_chart(pay_inst, "payment_installments.csv")

    # State coverage (seller state vs customer state). Mixed orders excluded.
    order_seller_states = oi[oi.order_id.isin(delivered_ids)].merge(sellers[["seller_id", "seller_state"]], on="seller_id", how="left")
    order_customer_state = delivered[["order_id", "customer_id"]].merge(customers[["customer_id", "customer_state"]], on="customer_id", how="left")
    state = order_seller_states.merge(order_customer_state, on="order_id", how="inner")
    state_group = state.groupby("order_id").agg(seller_states=("seller_state", lambda x: set(x.dropna())), customer_state=("customer_state", "first"))
    state_group["local_class"] = state_group.apply(lambda r: "all_local" if r.seller_states and all(s == r.customer_state for s in r.seller_states) else ("none_local" if r.seller_states and all(s != r.customer_state for s in r.seller_states) else "mixed"), axis=1)
    local = delivered.merge(state_group[["local_class"]], left_on="order_id", right_index=True, how="inner")
    local = local[local.local_class.isin(["all_local", "none_local"])].copy()
    local["carrier_to_customer_days"] = (local.order_delivered_customer_date-local.order_delivered_carrier_date).dt.total_seconds()/86400
    local_summary = local.groupby("local_class").agg(orders=("order_id", "nunique"), mean_carrier_to_customer_days=("carrier_to_customer_days", "mean")).reset_index()
    save_csv(local_summary, "local_seller_logistics.csv")
    local["approval_to_carrier_days"]=(local.order_delivered_carrier_date-local.order_approved_at).dt.total_seconds()/86400
    stages=local.groupby("local_class").agg(orders=("order_id","nunique"),approval_to_carrier_days=("approval_to_carrier_days","mean"),carrier_to_customer_days=("carrier_to_customer_days","mean")).reset_index()
    stages["group_label"]=stages.local_class.map({"all_local":"Todos os vendedores na mesma UF","none_local":"Nenhum vendedor na UF do cliente"})
    save_chart(stages, "logistics_stages.csv")
    save_chart(local_summary, "local_seller_logistics.csv")

    # Geographic approximation + robust OLS: use ZIP-prefix centroids; report association, not causation.
    # Restrict the large geolocation table to ZIP prefixes actually used by customers/sellers.
    used_zips = set(customers.customer_zip_code_prefix.dropna().unique()) | set(sellers.seller_zip_code_prefix.dropna().unique())
    geo = d["geo"].dropna(subset=["geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng"])
    geo = geo[geo.geolocation_zip_code_prefix.isin(used_zips)]
    geo_cent = geo.groupby("geolocation_zip_code_prefix", sort=False).agg(lat=("geolocation_lat", "mean"), lng=("geolocation_lng", "mean")).reset_index()
    cust_geo = customers[["customer_id", "customer_zip_code_prefix"]].merge(geo_cent, left_on="customer_zip_code_prefix", right_on="geolocation_zip_code_prefix", how="left").rename(columns={"lat":"cust_lat","lng":"cust_lng"})
    sell_geo = sellers[["seller_id", "seller_zip_code_prefix"]].merge(geo_cent, left_on="seller_zip_code_prefix", right_on="geolocation_zip_code_prefix", how="left").rename(columns={"lat":"sell_lat","lng":"sell_lng"})
    one_item = oi[oi.order_id.isin(delivered_ids)][["order_id","seller_id"]].drop_duplicates("order_id")
    lg = delivered[["order_id","customer_id","order_delivered_carrier_date","order_delivered_customer_date"]].merge(one_item,on="order_id").merge(cust_geo[["customer_id","cust_lat","cust_lng"]],on="customer_id").merge(sell_geo[["seller_id","sell_lat","sell_lng"]],on="seller_id")
    def haversine(a,b,c,e):
        a,b,c,e=np.radians([a,b,c,e]); h=np.sin((c-a)/2)**2+np.cos(a)*np.cos(c)*np.sin((e-b)/2)**2
        return 6371*2*np.arcsin(np.sqrt(h))
    lg["distance_km"] = haversine(lg.cust_lat,lg.cust_lng,lg.sell_lat,lg.sell_lng)
    lg["carrier_to_customer_days"]=(lg.order_delivered_customer_date-lg.order_delivered_carrier_date).dt.total_seconds()/86400
    reg=lg.dropna(subset=["distance_km","carrier_to_customer_days"])
    reg=reg[(reg.distance_km>0)&(reg.carrier_to_customer_days>=0)].copy()
    reg_export=reg[["order_id","distance_km","carrier_to_customer_days"]].copy()
    reg_export["log_distance"]=np.log1p(reg_export.distance_km)
    save_chart(reg_export, "geographic_regression_data.csv")
    regression_result = {}
    if len(reg)>30:
        # Modelo ajustado: distância + indicador de mesma UF (proxy de operação local).
        # O coeficiente de mesma UF é a diferença condicional estimada em dias.
        cust_state = customers[["customer_id", "customer_state"]]
        seller_state = sellers[["seller_id", "seller_state"]]
        reg = reg.merge(cust_state, on="customer_id", how="left").merge(seller_state, on="seller_id", how="left")
        reg["same_state"] = (reg.customer_state == reg.seller_state).astype(int)
        X = sm.add_constant(pd.DataFrame({
            "same_state": reg.same_state,
            "log_distance": np.log1p(reg.distance_km)
        }))
        fit = sm.OLS(reg.carrier_to_customer_days, X).fit(cov_type="HC3")
        regression_result = {
            "n": int(fit.nobs),
            "same_state_effect_days": float(fit.params["same_state"]),
            "ci95_low": float(fit.conf_int().loc["same_state", 0]),
            "ci95_high": float(fit.conf_int().loc["same_state", 1]),
            "distance_log_coefficient": float(fit.params["log_distance"]),
            "p_value": float(fit.pvalues["same_state"]),
            "r_squared": float(fit.rsquared),
            "model": "carrier_to_customer_days ~ same_state + log1p(distance_km)"
        }

    # Northeast representation among unique customers and active sellers (delivered orders).
    cust_ne = customers[customers.customer_state.isin(["AL","BA","CE","MA","PB","PE","PI","RN","SE"])]
    active_seller_ids = oi[oi.order_id.isin(delivered_ids)].seller_id.unique()
    active_sellers = sellers[sellers.seller_id.isin(active_seller_ids)]
    seller_ne = active_sellers[active_sellers.seller_state.isin(["AL","BA","CE","MA","PB","PE","PI","RN","SE"])]
    region_map={"Sudeste":"SE","Sul":"S","Nordeste":"NE","Centro-Oeste":"CO","Norte":"N"}
    state_region={"SP":"Sudeste","RJ":"Sudeste","MG":"Sudeste","ES":"Sudeste","PR":"Sul","SC":"Sul","RS":"Sul","AL":"Nordeste","BA":"Nordeste","CE":"Nordeste","MA":"Nordeste","PB":"Nordeste","PE":"Nordeste","PI":"Nordeste","RN":"Nordeste","SE":"Nordeste","DF":"Centro-Oeste","GO":"Centro-Oeste","MT":"Centro-Oeste","MS":"Centro-Oeste","AC":"Norte","AP":"Norte","AM":"Norte","PA":"Norte","RO":"Norte","RR":"Norte","TO":"Norte"}
    freight_by_order=oi.groupby("order_id").freight_value.sum()
    reg_rows=[]
    cust_region=customers[customers.customer_id.isin(o.customer_id)].copy(); cust_region["region"]=cust_region.customer_state.map(state_region)
    active_sellers2=active_sellers.copy(); active_sellers2["region"]=active_sellers2.seller_state.map(state_region)
    for region in ["Sudeste","Sul","Nordeste","Centro-Oeste","Norte"]:
        c=cust_region[cust_region.region.eq(region)]
        ss=active_sellers2[active_sellers2.region.eq(region)]
        od=delivered.merge(customers[["customer_id","customer_state"]],on="customer_id",how="left")
        od=od[od.customer_state.map(state_region).eq(region)]
        reg_rows.append({"region":region,"customers":c.customer_unique_id.nunique(),"customer_share_pct":c.customer_unique_id.nunique()/cust_region.customer_unique_id.nunique()*100,"active_sellers":ss.seller_id.nunique(),"seller_share_pct":ss.seller_id.nunique()/active_sellers2.seller_id.nunique()*100,"orders":od.order_id.nunique(),"avg_freight_brl":od.order_id.map(freight_by_order).mean() if len(od) else np.nan,"avg_delivery_days":od.order_id.map(delivered.set_index("order_id").lead_days).mean() if len(od) else np.nan,"late_rate":od.order_id.map(delivered.set_index("order_id").late).mean() if len(od) else np.nan})
    save_chart(pd.DataFrame(reg_rows), "regional_distribution.csv")

    # Simple trend forecast: monthly order counts Jan-Aug 2018, linear OLS and 80% prediction intervals.
    m18 = monthly[monthly.month.str.startswith("2018-")].copy().sort_values("month")
    m18 = m18[m18.month <= "2018-08"]
    forecast = {}
    if len(m18)>=4:
        x=np.arange(len(m18),dtype=float); y=m18.orders.to_numpy(dtype=float)
        model=sm.OLS(y,sm.add_constant(x)).fit()
        xf=np.arange(len(m18),len(m18)+4,dtype=float)
        pred=model.get_prediction(sm.add_constant(xf)).summary_frame(alpha=.20)
        fdf=pd.DataFrame({"month":[f"2018-{m:02d}" for m in range(9,13)],"forecast_orders":pred["mean"].clip(lower=0),"lower_80":pred["obs_ci_lower"].clip(lower=0),"upper_80":pred["obs_ci_upper"].clip(lower=0)})
        save_csv(fdf,"orders_forecast_sep_dec_2018.csv")
        save_chart(fdf,"orders_forecast_sep_dec_2018.csv")
        # Backtest: train Jan-Aug 2017 and predict Sep-Dec 2017, WAPE.
        m17=monthly[monthly.month.str.startswith("2017-")].sort_values("month")
        m17=m17[m17.month<="2017-08"]
        wape=None
        if len(m17)>=4:
            mm=sm.OLS(m17.orders.to_numpy(float),sm.add_constant(np.arange(len(m17),dtype=float))).fit()
            bp=mm.predict(sm.add_constant(np.arange(len(m17),len(m17)+4,dtype=float))).clip(0)
            actual=monthly[monthly.month.isin([f"2017-{m:02d}" for m in range(9,13)])].orders.sum()
            wape=float(np.abs(bp-np.array(monthly.set_index('month').reindex([f"2017-{m:02d}" for m in range(9,13)]).orders.fillna(0))).sum()/max(actual,1))
        forecast={"slope_orders_per_month":float(model.params[1]),"backtest_wape":wape,"method":"linear trend; no seasonality or event adjustment"}

    total_orders=int(o.order_id.nunique())
    metrics={
        "dataset_scope":{"orders":total_orders,"unique_customers":int(customers[customers.customer_id.isin(o.customer_id)].customer_unique_id.nunique()),"period_start":"2017-01-01","period_end_exclusive":"2018-09-01"},
        "commercial":{"gmv_all_status_brl":money(oi.gross_value.sum()),"product_ticket_mean_brl":money(order_product.product_value.mean()),"semester":semester.to_dict(orient="records")},
        "delivery":{"delivered_orders":int(delivered.order_id.nunique()),"mean_purchase_to_delivery_days":money(delivered.lead_days.mean()),"late_rate":float(delivered.late.mean())},
        "reviews_by_delivery_status":review_summary.to_dict(orient="records"),
        "seller_concentration":concentration,
        "repeat_purchase":{"cohort_customers":int(len(first)),"fisher_exact_p_value":float(repeat_p),"by_delivery_status":repeat.to_dict(orient="records"),"delivery_date_sensitivity_p_value":float(repeat_delivery_p),"delivery_date_sensitivity":repeat_delivery_sensitivity.to_dict(orient="records")},
        "payments":{"credit_card_share_of_paid_value":float(pay_mix.get("credit_card",0)/pay_mix.sum()),"credit_card_orders_installments_gt1_share":float((cc_order_installments>1).mean()) if len(cc_order_installments) else None,"median_credit_card_installments":float(cc_order_installments.median()) if len(cc_order_installments) else None},
        "logistics_local_seller":local_summary.to_dict(orient="records"),
        "geographic_distance_regression":regression_result,
        "northeast":{"customer_share":float(cust_ne.customer_unique_id.nunique()/customers.customer_unique_id.nunique()),"active_seller_share":float(seller_ne.seller_id.nunique()/active_sellers.seller_id.nunique()) if len(active_sellers) else None},
        "forecast":forecast,
        "methodological_notes":["GMV = item price + freight; it is not accounting revenue or profit.","Product ticket = mean sum of item prices per order; freight excluded.","On-time means delivered on or before estimated delivery date.","Seller local classification uses seller/customer state; mixed orders excluded.","Distance is approximated from ZIP-prefix centroids; regression controls for log distance and same-state indicator; association, not causation.","Forecast is a linear trend without seasonality or Black Friday adjustment."]
    }
    (OUT/"metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    manifest={"source":"data/*.csv","generated_by":"src/analysis.py","files":{f.name:{"rows":int(len(pd.read_csv(f))),"columns":list(pd.read_csv(f,nrows=0).columns)} for f in sorted(CHART.glob("*.csv"))}}
    (CHART/"chart_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Análise concluída. Resultados em outputs/metrics.json, outputs/*.csv e outputs/chart_data/.")
    print(json.dumps({k:metrics[k] for k in ["dataset_scope","commercial","delivery","seller_concentration","forecast"]},ensure_ascii=False,indent=2,default=str))

if __name__ == "__main__":
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        main()
