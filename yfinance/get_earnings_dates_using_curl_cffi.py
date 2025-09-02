from io import StringIO
from bs4 import BeautifulSoup
import pandas as pd
from typing import Optional
from dateutil import parser
from zoneinfo import ZoneInfo


def get_earnings_dates_using_curl_cffi(
    _data, limit: int = 100, offset: int = 0, ticker: str = "AAPL"
) -> Optional[pd.DataFrame]:
    """
    Uses curl_cffi to scrap earnings data from YahooFinance.
    (https://finance.yahoo.com/calendar/earnings)

    Args:
        limit (int): Number of rows to extract (max=100)
        ticker (str): Ticker to search for

    Returns:
        pd.DataFrame in the following format.

                   EPS Estimate Reported EPS Surprise(%)
        Date
        2025-10-30         2.97            -           -
        2025-07-22         1.73         1.54      -10.88
        2025-05-06         2.63          2.7        2.57
        2025-02-06         2.09         2.42       16.06
        2024-10-31         1.92         1.55      -19.36
        ...                 ...          ...         ...
        2014-07-31         0.61         0.65        7.38
        2014-05-01         0.55         0.68       22.92
        2014-02-13         0.55         0.58        6.36
        2013-10-31         0.51         0.54        6.86
        2013-08-01         0.46          0.5        7.86
    """
    #####################################################
    # Define Constants
    #####################################################
    unique_class_id_for_table = "yf-7uw1qi bd"
    if limit > 0 and limit <= 25:
        size = 25
    elif limit > 25 and limit <= 50:
        size = 50
    elif limit > 50 and limit <= 100:
        size = 100
    else:
        raise ValueError("Please use limit <= 100")

    # Define the URL
    url = "https://finance.yahoo.com/calendar/earnings?symbol={}&offset={}&size={}".format(
        ticker, offset, size
    )
    #####################################################
    # End of Constants
    #####################################################

    # Use YfData.cache_get
    response = _data.cache_get(url)
    # Check if the request was successful
    response.raise_for_status()
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")
    # Find the table by a unique identifier
    # You'd need to inspect the page's HTML to find the correct attributes
    # For Yahoo Finance, the earnings table often has a specific class or data attribute.
    table = soup.find("table", {"class": unique_class_id_for_table})
    # If the table is found
    if table:
        # Get the HTML string of the table
        table_html = str(table)

        # Wrap the HTML string in a StringIO object
        html_stringio = StringIO(table_html)

        # Pass the StringIO object to pd.read_html()
        df = pd.read_html(html_stringio)[0]
        df = df.dropna(subset=["Symbol", "Company", "Earnings Date"])

        # praser.parse doesn't understand "EDT", "EST"
        tzinfos = {
            "EDT": ZoneInfo("America/New_York"),
            "EST": ZoneInfo("America/New_York"),
        }
        df.index = df["Earnings Date"].apply(
            lambda date_str: parser.parse(date_str, tzinfos=tzinfos).strftime(
                "%Y-%m-%d"
            )
        )
        df.index.name = "Date"
        # Remove "+" sign from Surprise(%)
        df["Surprise (%)"] = df["Surprise (%)"].apply(
            lambda x: str(x[1:]) if x[0] == "+" else str(x)
        )
        df = df.drop(["Earnings Date", "Company", "Symbol"], axis=1)

    else:
        raise ValueError("Table not found on the page.")

    return df
