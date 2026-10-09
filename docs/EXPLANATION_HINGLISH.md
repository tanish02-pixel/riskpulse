# RiskPulse ko simple language mein samjho

## Hum kya bana rahe hain?

Ek financial news reader + AI risk engine + mock stock index dashboard. News aur company announcements ka text aata hai. Engine batata hai tone positive/negative/neutral hai, event kis type ka hai, aur severity kitni ho sakti hai. Phir Module A company sentiment ke basis par mock portfolio weights adjust karta hai.

**Mock portfolio mein real money/trading nahi hoti.** Ten companies start mein 10% each hoti hain. Synthetic example mein Apple ki positive earnings se Apple ka target badhta hai. JPMorgan ki fictional credit problem se uska target ghatta hai. Total allocation 100% rehta hai.

## Three required outputs

| Output | Matlab | Example |
|---|---|---|
| Sentiment Score | Text ka financial tone, -1 se +1 | Negative credit text: around -0.94 |
| Event Classification | Kis tarah ki news | Credit Event |
| Impact Score | Rule-based severity, 1 se 10 | 9/10 |

Impact 9 ka matlab stock 9% girega nahi hai. Woh severity estimate hai. Sentiment bhi future return ki guarantee nahi hai.

## App ke andar kya dekhna hai?

- **Overview:** processed texts, sentiment summary, high-impact signals, current weights.
- **Risk signals:** headline, ticker, score, event, impact. Row click karne par analyzed text aur evidence.
- **Index allocation:** 10% baseline versus current weights, saved history, latest change.
- **Data sources:** BBC/Apple/Microsoft fetch status. Errors bhi visible hote hain.
- **Policy settings:** minimum/maximum weights, turnover, confidence and freshness limits. Active model bhi yahin check karo.
- **Project guide:** app ke andar explanation aur demo flow.

## Live aur replay ka difference

Live mode internet se actual provider texts laata hai. Purani/global/neutral news portfolio ko change nahi bhi kar sakti. Replay mode mein 12 fictional examples hain. Demo ke liye predictable hai aur clearly Synthetic label dikhata hai. Dono modes ke portfolios alag hain. Jury ko honestly batao kaunsa mode dikha rahe ho.

## Laptop par start kaise karna hai?

1. ZIP download karke Extract All karo.
2. Python 3.11+ install hona chahiye.
3. `riskpulse/start.bat` double-click karo.
4. Browser mein `http://127.0.0.1:8000` kholo.
5. Pehle base setup check karo. Phir server stop karo, `scripts/enable_finbert.bat` chalao, model download hone do, aur `start.bat` restart karo.
6. Policy settings mein active model **finbert** check karo. Model download pehli baar internet aur disk space lega.
7. Synthetic replay select karo aur Run synthetic scenario click karo. Index allocation kholo.

## Jury ko bolne ke liye short intro

"RiskPulse implements the unified financial NLP risk engine and Module A. It ingests financial news and first-party company announcements, generates sentiment, event and severity fields, and uses eligible sentiment to rebalance a ten-stock mock index. FinBERT provides financial sentiment. Auditable rules provide event labels and severity estimates. SQLite preserves the signal evidence and weight history. Live feeds and synthetic replay stay separate."

## Questions ka answer kaise dena hai?

**Why FinBERT?** Financial language ke liye pretrained sentiment model hai. Humne naya model train karne ka claim nahi kiya.

**Why no Module B?** Brief mein at least one module chahiye. Humne Module A ko fully implement kiya. API future stress-testing consumer ke liye event/impact fields deta hai.

**Weight kaise change hota hai?** Fresh, confident company signal ko higher importance milti hai. Source coefficient aur time decay apply hota hai. Equal baseline ka target sentiment se tilt hota hai. Phir floor/cap aur turnover controls apply hote hain.

**Accuracy kitni hai?** 24 synthetic sanity cases mein labels match hue. Yeh real-news benchmark nahi hai. 28 automated tests implementation checks hain, investment performance proof nahi.

**If internet fails?** Cached model + labeled synthetic replay local demo chala sakte hain. Live fetch error honestly show hoga.

**AI use?** `AI_USAGE.md` mein disclosure diya hai. Organizer ke exact rules padho. Code samjho aur khud run karke verify karo before presenting.
