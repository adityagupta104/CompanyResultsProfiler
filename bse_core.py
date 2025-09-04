# bse_core.py
import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd

import requests
from bs4 import BeautifulSoup

# -------------------------
# Core BSE functions
# -------------------------
def get_bse_data_by_config(scrip_code, from_date, to_date, config):
    """
    Fetch announcements from BSE for a single config and date range.
    """
    url = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"
    params = {
        "pageno": 1,
        "strCat": config.get("category"),
        "strPrevDate": from_date,
        "strScrip": scrip_code,
        "strSearch": "P",
        "strToDate": to_date,
        "strType": "C",
        "subcategory": config.get("subcategory", "-1")
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.bseindia.com",
        "Referer": "https://www.bseindia.com/"
    }
    print("calling for a request to BSE %s from %s to %s" % (config["name"], from_date, to_date))
    r = requests.get(url, params=params, headers=headers)
    r.raise_for_status()
    data = r.json()

    results = []
    for item in data.get("Table", []):
        desc = (item.get("NEWSSUB") or "").lower()
        headline = (item.get("HEADLINE") or "").lower()
        combined = f"{headline} {desc}"

        # Apply filter if specified
        if config.get("filter") and config["filter"].lower() not in combined:
            continue

        pdf_link = item.get("ATTACHMENTNAME")
        if pdf_link and not pdf_link.startswith("http"):
            pdf_link = "https://www.bseindia.com/xml-data/corpfiling/AttachHis/" + pdf_link

        raw_date = item.get("NEWS_DT")
        try:
            if "." in raw_date:
                raw_date = raw_date.split(".")[0]
            parsed_date = datetime.strptime(raw_date, "%Y-%m-%dT%H:%M:%S")
            date_str = parsed_date.strftime("%Y-%m-%d")
        except Exception:
            date_str = raw_date

        results.append({
            "Config": config["name"],
            "Date": date_str,
            "Headline": item.get("HEADLINE"),
            "Title": item.get("NEWSSUB"),
            "Link": pdf_link,
            "Quarter": None,
            "FiscalYear": None
        })

    return pd.DataFrame(results)


def get_quarter_dates(q, fy):
    """
    Given a quarter (1-4) and fiscal year, return start and end dates in YYYYMMDD format.
    """
    if q == 1:
        start = datetime(fy-1, 4, 1)
    elif q == 2:
        start = datetime(fy-1, 7, 1)
    elif q == 3:
        start = datetime(fy-1, 10, 1)
    elif q == 4:
        start = datetime(fy, 1, 1)
    else:
        raise ValueError("Quarter must be 1–4")
    end = start + relativedelta(months=3, days=-1)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def get_quarter_data(scrip_code, quarter, fiscal_year, configs):
    """
    Fetch BSE data for a single quarter using multiple configs.
    """
    dfs = []
    seen_names = set()
    q_start, q_end = get_quarter_dates(quarter, fiscal_year)
    next_q = (quarter % 4) + 1
    next_fy = fiscal_year + 1 if quarter == 4 else fiscal_year
    next_start, next_end = get_quarter_dates(next_q, next_fy)

    for config in configs:
        if config["name"] in seen_names:
            continue

        if config.get("lookahead", False):
            from_date, to_date = next_start, next_end
        else:
            from_date, to_date = q_start, q_end

        df = get_bse_data_by_config(scrip_code, from_date, to_date, config)
        if not df.empty:
            df["Quarter"] = quarter
            df["FiscalYear"] = fiscal_year
            dfs.append(df)
            seen_names.add(config["name"])

    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)


def get_range_quarters_data(scrip_code, start_q, start_fy, end_q, end_fy, configs):
    """
    Fetch BSE data for multiple quarters in a range.
    """
    dfs = []
    q, fy = start_q, start_fy

    while (fy < end_fy) or (fy == end_fy and q <= end_q):
        df = get_quarter_data(scrip_code, q, fy, configs)
        if not df.empty:
            dfs.append(df)

        # Move to next quarter
        if q == 4:
            q = 1
            fy += 1
        else:
            q += 1

    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)


def search_bse_company(query: str):
    """
    Search BSE for a company by name/ticker and return a list of matches with scrip codes.
    """
    url = "https://api.bseindia.com/Msource/1D/getQouteSearch.aspx"
    params = {
        "Type": "EQ",
        "text": query,
        "flag": "site"
    }
    headers = {
        "accept": "application/json, text/plain, */*",
        "origin": "https://www.bseindia.com",
        "referer": "https://www.bseindia.com/",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    }

    r = requests.get(url, params=params, headers=headers)
    r.raise_for_status()
    html = r.text

    soup = BeautifulSoup(html, "html.parser")
    results = []

    for li in soup.find_all("li", class_="quotemenu"):
        a_tag = li.find("a")
        if a_tag and a_tag.get("id"):
            href_parts = a_tag.get("id").strip("/").split("/")
            company_name = a_tag.find("span").text
            #company_name = a_tag.get_text(separator="\n").split("\n")[0].strip()
            scrip_code = href_parts[-1]  # last part is the scrip code
            results.append({"name": company_name, "scrip_code": scrip_code})

    return results

if __name__ == "__main__":
    
    configs = [
    {"name": "results", "category": "Result", "lookahead": True},  
    {"name": "results", "category": "Board Meeting", "filter": "result", "lookahead": True},  
    {"name": "presentation", "category": "Company Update", "filter": "presentation", "lookahead": True},
    {"name": "transcript", "category": "Company Update", "filter": "transcript", "lookahead": True}
]

    scrip_code = "500180"  # Example scrip code
    df = get_range_quarters_data(scrip_code, 3, 2024, 4, 2025, configs)

    print(df)

    from itables import show
    show(df,render_in_browser=True)

    pivot_df = pivot_announcement_links(df)
    print(pivot_df)
    
    #search_bse_company("balaji")

