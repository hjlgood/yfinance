from urllib.parse import urlsplit, urljoin
from bs4 import BeautifulSoup
from curl_cffi import requests


def _is_this_consent_url(response_url: str) -> bool:
    try:
        return urlsplit(response_url).hostname and urlsplit(
            response_url
        ).hostname.endswith("consent.yahoo.com")
    except Exception:
        return False


def _accept_consent_form(
    session: requests.Session, consent_resp: requests.Response, timeout: int
) -> requests.Response:
    soup = BeautifulSoup(consent_resp.text, "html.parser")

    # Heuristic: pick the first form; Yahoo's CMP tends to have a single form for consent
    form = soup.find("form")
    if not form:
        return consent_resp

    # action : URL to send "Accept Cookies"
    action = form.get("action") or consent_resp.url
    action = urljoin(consent_resp.url, action)

    # Collect inputs (hidden tokens, etc.)
    """
    <input name="csrfToken" type="hidden" value="..."/>
    <input name="sessionId" type="hidden" value="..."/>
    <input name="originalDoneUrl" type="hidden" value="..."/>
    <input name="namespace" type="hidden" value="yahoo"/>
    """
    data = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        if not name:
            continue
        typ = (inp.get("type") or "text").lower()
        val = inp.get("value") or ""

        if typ in ("checkbox", "radio"):
            # If it's clearly an "agree"/"accept" field or already checked, include it
            if (
                "agree" in name.lower()
                or "accept" in name.lower()
                or inp.has_attr("checked")
            ):
                data[name] = val if val != "" else "1"
        else:
            data[name] = val

    # If no explicit agree/accept in inputs, add a best-effort flag
    lowered = {k.lower() for k in data.keys()}
    if not any(("agree" in k or "accept" in k) for k in lowered):
        data["agree"] = "1"

    # Submit the form with "Referer". Some servers check this header as a simple CSRF protection measure.
    headers = {"Referer": consent_resp.url}
    return session.post(
        action, data=data, headers=headers, timeout=timeout, allow_redirects=True
    )
