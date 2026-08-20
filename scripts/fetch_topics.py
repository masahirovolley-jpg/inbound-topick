import json, re, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
import feedparser, requests
from bs4 import BeautifulSoup

SOURCES = [
 {"name":"JNTO","url":"https://www.jnto.go.jp/","pages":["https://www.jnto.go.jp/news/"],"feeds":["https://www.jnto.go.jp/news/rss.xml"]},
 {"name":"Travel Voice","url":"https://www.travelvoice.jp/","pages":["https://www.travelvoice.jp/"],"feeds":["https://www.travelvoice.jp/feed"]},
 {"name":"やまとごころ.jp","url":"https://yamatogokoro.jp/","pages":["https://yamatogokoro.jp/"],"feeds":["https://yamatogokoro.jp/feed/"]},
 {"name":"時事ドットコム","url":"https://www.jiji.com/","pages":["https://www.jiji.com/jc/c?g=eco"],"feeds":["https://www.jiji.com/rss/ranking.rdf"]},
 {"name":"訪日ラボ","url":"https://honichi.com/","pages":["https://honichi.com/news/"],"feeds":["https://honichi.com/feed/"]},
]
HEADERS={"User-Agent":"InboundPulse/1.0 (+https://github.com/masahirovolley-jpg/inbound-topick)"}
KEYWORDS=re.compile(r"訪日|インバウンド|観光|旅行|宿泊|ホテル|航空|鉄道|空港|旅客|外国人|ツーリズム|touris",re.I)

def clean(value, limit=150):
 text=BeautifulSoup(value or "","html.parser").get_text(" ",strip=True)
 text=re.sub(r"\s+"," ",text)
 return text[:limit]+("…" if len(text)>limit else "")

def iso(value):
 if not value:return None
 try:return datetime(*value[:6],tzinfo=timezone.utc).isoformat()
 except Exception:return None

def from_feed(source):
 for feed_url in source["feeds"]:
  try:
   response=requests.get(feed_url,headers=HEADERS,timeout=20);response.raise_for_status()
   feed=feedparser.parse(response.content)
   if feed.entries:
    return [{"source":source["name"],"title":clean(e.get("title"),110),"summary":clean(e.get("summary") or e.get("description")),"url":e.get("link"),"published":iso(e.get("published_parsed") or e.get("updated_parsed"))} for e in feed.entries[:20] if e.get("title") and e.get("link")]
  except Exception as exc: print(f"Feed failed {feed_url}: {exc}")
 return []

def from_page(source):
 for page in source["pages"]:
  try:
   response=requests.get(page,headers=HEADERS,timeout=20);response.raise_for_status();soup=BeautifulSoup(response.text,"html.parser");rows=[]
   for a in soup.select("a[href]"):
    title=clean(a.get_text(" ",strip=True),110);url=urljoin(page,a.get("href"))
    if len(title)<16 or urlparse(url).netloc!=urlparse(source["url"]).netloc:continue
    if source["name"]=="時事ドットコム" and not KEYWORDS.search(title):continue
    container=a.find_parent(["article","li","div"]);stamp=None
    if container:
     t=container.find("time")
     if t: stamp=t.get("datetime") or clean(t.get_text())
    rows.append({"source":source["name"],"title":title,"summary":"","url":url,"published":stamp})
   if rows:return rows[:20]
  except Exception as exc: print(f"Page failed {page}: {exc}")
 return []

def main():
 articles=[]
 for source in SOURCES:
  rows=from_feed(source) or from_page(source);articles.extend(rows);print(source["name"],len(rows));time.sleep(1)
 seen=set();unique=[]
 for item in articles:
  key=item["url"].split("#")[0]
  if key in seen:continue
  seen.add(key);item["url"]=key;unique.append(item)
 output={"updated_at":datetime.now(timezone.utc).isoformat(),"sources":[{"name":s["name"],"url":s["url"]} for s in SOURCES],"articles":unique}
 path=Path(__file__).parents[1]/"data"/"topics.json";path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
 if not unique:raise SystemExit("No articles were collected")

if __name__=="__main__":main()
