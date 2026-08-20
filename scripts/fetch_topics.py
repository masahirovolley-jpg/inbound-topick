import hashlib, json, re, time
from difflib import SequenceMatcher
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
import feedparser, requests
from bs4 import BeautifulSoup

SOURCES = [
 {"name":"JNTO","url":"https://www.jnto.go.jp/","pages":["https://www.jnto.go.jp/news/"],"feeds":["https://www.jnto.go.jp/news/rss.xml"]},
 {"name":"観光庁","url":"https://www.mlit.go.jp/kankocho/","pages":["https://www.mlit.go.jp/kankocho/"],"feeds":[]},
 {"name":"Travel Voice","url":"https://www.travelvoice.jp/","pages":["https://www.travelvoice.jp/"],"feeds":["https://www.travelvoice.jp/feed"]},
 {"name":"やまとごころ.jp","url":"https://yamatogokoro.jp/","pages":["https://yamatogokoro.jp/"],"feeds":["https://yamatogokoro.jp/feed/"]},
 {"name":"時事ドットコム","url":"https://www.jiji.com/","pages":["https://www.jiji.com/jc/c?g=eco"],"feeds":["https://www.jiji.com/rss/ranking.rdf"]},
 {"name":"訪日ラボ","url":"https://honichi.com/","pages":["https://honichi.com/news/"],"feeds":["https://honichi.com/feed/"]},
]
HEADERS={"User-Agent":"InboundPulse/1.0 (+https://github.com/masahirovolley-jpg/inbound-topick)"}
KEYWORDS=re.compile(r"訪日|インバウンド|観光|旅行|宿泊|ホテル|航空|鉄道|空港|旅客|外国人|ツーリズム|touris",re.I)
CATEGORIES=[("統計・市場動向",r"統計|調査|推計|消費額|客数|宿泊|ランキング|市場|需要|前年比|データ"),("政策・制度",r"政策|制度|法|規制|税|ビザ|査証|入国|公募|補助|予算|行政|政府"),("航空・交通",r"航空|空港|鉄道|新幹線|交通|旅客|クルーズ|路線|運航"),("宿泊・施設",r"ホテル|旅館|宿泊|民泊|商業施設|百貨店"),("地域・DMO",r"地域|自治体|DMO|地方|まちづくり|観光地"),("AI・デジタル",r"AI|デジタル|DX|テクノロジー|予約|プラットフォーム|SNS"),("サステナブル",r"サステナ|持続可能|環境|オーバーツーリズム|脱炭素")]

def clean(value, limit=150):
 text=BeautifulSoup(value or "","html.parser").get_text(" ",strip=True)
 text=re.sub(r"\s+"," ",text)
 return text[:limit]+("…" if len(text)>limit else "")

def iso(value):
 if not value:return None
 try:return datetime(*value[:6],tzinfo=timezone.utc).isoformat()
 except Exception:return None

def category(text):
 for name,pattern in CATEGORIES:
  if re.search(pattern,text,re.I):return name
 return "業界ニュース"

def feed_image(entry):
 for key in ("media_content","media_thumbnail"):
  values=entry.get(key) or []
  if values and values[0].get("url"):return values[0]["url"]
 for item in entry.get("enclosures") or []:
  if str(item.get("type","")).startswith("image/"):return item.get("href")
 soup=BeautifulSoup(entry.get("summary") or entry.get("description") or "","html.parser");img=soup.find("img")
 return img.get("src") if img else None

def from_feed(source):
 for feed_url in source["feeds"]:
  try:
   response=requests.get(feed_url,headers=HEADERS,timeout=20);response.raise_for_status()
   feed=feedparser.parse(response.content)
   if feed.entries:
    rows=[{"source":source["name"],"title":clean(e.get("title"),110),"summary":clean(e.get("summary") or e.get("description")),"url":e.get("link"),"published":iso(e.get("published_parsed") or e.get("updated_parsed")),"image_url":feed_image(e)} for e in feed.entries[:20] if e.get("title") and e.get("link")]
    if source["name"]=="時事ドットコム": rows=[r for r in rows if KEYWORDS.search(r["title"]+" "+r["summary"])]
    if rows:return rows
  except Exception as exc: print(f"Feed failed {feed_url}: {exc}")
 return []

def from_page(source):
 for page in source["pages"]:
  try:
   response=requests.get(page,headers=HEADERS,timeout=20);response.raise_for_status();soup=BeautifulSoup(response.content,"html.parser");rows=[]
   for a in soup.select("a[href]"):
    title=clean(a.get_text(" ",strip=True),110);url=urljoin(page,a.get("href"))
    if len(title)<16 or urlparse(url).netloc!=urlparse(source["url"]).netloc:continue
    if source["name"]=="時事ドットコム" and not KEYWORDS.search(title):continue
    container=a.find_parent(["article","li"]) or a.find_parent("div");stamp=None
    if container:
     t=container.find("time")
     if t: stamp=t.get("datetime") or clean(t.get_text())
     if source["name"]=="観光庁":
      match=re.search(r"(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日",container.get_text(" ",strip=True))
      if match: stamp=f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    if source["name"]=="観光庁" and not stamp:continue
    img=container.find("img") if container else None
    rows.append({"source":source["name"],"title":title,"summary":"","url":url,"published":stamp,"image_url":urljoin(page,img.get("src") or img.get("data-src")) if img and (img.get("src") or img.get("data-src")) else None})
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
  seen.add(key);item["url"]=key;item["category"]=category(item["title"]+" "+item["summary"]);unique.append(item)
 for i,item in enumerate(unique):
  normalized=re.sub(r"[\W_]+","",item["title"]);group=None
  for prev in unique[:i]:
   pnorm=re.sub(r"[\W_]+","",prev["title"])
   if SequenceMatcher(None,normalized,pnorm).ratio()>=0.48:group=prev["topic_group"];break
  item["topic_group"]=group or hashlib.sha1(normalized.encode()).hexdigest()[:10]
 for item in sorted(unique,key=lambda x:x.get("published") or "",reverse=True)[:12]:
  if item.get("image_url"):continue
  try:
   page=requests.get(item["url"],headers=HEADERS,timeout=12);soup=BeautifulSoup(page.content,"html.parser");meta=soup.select_one('meta[property="og:image"]')
   if meta and meta.get("content"):item["image_url"]=urljoin(item["url"],meta["content"])
  except Exception:pass
 output={"updated_at":datetime.now(timezone.utc).isoformat(),"sources":[{"name":s["name"],"url":s["url"]} for s in SOURCES],"articles":unique}
 path=Path(__file__).parents[1]/"data"/"topics.json";path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
 if not unique:raise SystemExit("No articles were collected")

if __name__=="__main__":main()
