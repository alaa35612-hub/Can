أنت Codex Agent خبير Python وBinance Futures وMarket Microstructure.

المطلوب: ابنِ مشروع Python احترافي في ملف واحد فقط باسم:

structural_liquidity_scanner_v321_dynamic.py

الهدف ليس كتابة قواعد ثابتة، بل تحويل شجرة القرار V3.2.1 إلى محرك كشف ديناميكي ذكي يمسح كل عملات Binance USD-M Futures ويصنف البنية البنيوية لكل عملة حسب:

Data Quality / Regime Check
→ Dynamic Baseline
→ Phase Memory
→ OI Value / Quote Volume Validation
→ Price State
→ OI State
→ L/S Structure
→ Trades Regime
→ Price Acceptance
→ Structural Pre-Scanner
→ Trigger / Post-Trigger Check
→ Price-led Reset Ignition Check
→ Price-led Base Ignition Check
→ Price-led Base Vacuum Ignition Check
→ High OI Compression
→ Conflict Resolution
→ Readiness Confirmation Level
→ Final Structural Decision

ممنوع بناء النظام بهذا الترتيب الخاطئ:
Price → OI → L/S → Trades → Decision

المطلوب أن يكون الكود كاملًا وقابلًا للتشغيل مباشرة بدون ملفات إضافية.

============================================================

1) شروط عامة إجبارية
   ============================================================

- ملف Python واحد فقط.
- الإعدادات كلها في أعلى الملف داخل CONFIG أو SETTINGS.
- لا تستخدم أرقام ثابتة جامدة لاكتشاف الأنماط.
- الأرقام التشغيلية مسموحة فقط في الإعدادات مثل:
  timeframe, limit, scan interval, top_n, request timeout, retry count.
- أي Threshold تحليلي يجب أن يكون ديناميكيًا من بيانات العملة نفسها:
  rolling median, MAD, robust z-score, percentile rank, quantiles, local baseline, regime baseline.
- لا تستخدم RSI كعامل قرار. RSI سياق بصري فقط.
- لا تستخدم شمعة واحدة لاتخاذ القرار.
- يجب قراءة آخر عدة شموع مع Phase Memory.
- ممنوع lookahead.
- يجب أن يعمل Live Scanner على آخر البيانات فقط.
- يجب أن يطبع النتائج في Console.
- يجب أن يحفظ النتائج في CSV و JSON.
- يجب أن يكون هناك وضعان:
  early_watch
  strict_live
- يجب أن يكون الكود منظمًا داخل Classes / dataclasses / functions واضحة.
- لا تعتمد على API keys. استخدم Binance public endpoints فقط.
- يجب التعامل مع أخطاء الشبكة والـ rate limit والبيانات الناقصة.
- لا تسقط العملة فقط لأن OI ثابت أو هابط قليلًا إذا تحققت شروط Price-led Base Vacuum Ignition.

============================================================
2) إعدادات أعلى الملف

ضع في أعلى الملف CONFIG يشمل على الأقل:

MODE = "early_watch" أو "strict_live"
TIMEFRAME = "15m"
LIMIT = 150 أو 200
SCAN_ALL_USDT_PERPETUALS = True
SYMBOL_WHITELIST = []
SYMBOL_BLACKLIST = ["BTCUSDT", "ETHUSDT"] اختياري
TOP_N_RESULTS = 30
SAVE_CSV = True
SAVE_JSON = True
AUTO_RUN = True
SLEEP_BETWEEN_REQUESTS
REQUEST_TIMEOUT
RETRY_COUNT
MIN_CANDLES_REQUIRED
OUTPUT_DIR
USE_FUNDING_CONTEXT = True
USE_OI_VALUE_VALIDATION = True
USE_QUOTE_VOLUME_VALIDATION = True
PRINT_DEBUG_PER_SYMBOL = False

لكن لا تجعل هذه الإعدادات Thresholds جامدة للتصنيف البنيوي.

============================================================
3) جلب البيانات من Binance Futures

ابنِ BinanceFuturesClient داخل نفس الملف.

اجلب البيانات التالية لكل عملة USDT Perpetual:

- Klines:
  close
  high
  low
  open
  volume
  quote_volume
  number_of_trades
  timestamps

Endpoint:
GET https://fapi.binance.com/fapi/v1/klines

- OI history:
  open_interest
  timestamp

Endpoint:
GET https://fapi.binance.com/futures/data/openInterestHist

- Global Long/Short Account Ratio:
  Endpoint:
  GET https://fapi.binance.com/futures/data/globalLongShortAccountRatio

- Top Trader Long/Short Account Ratio:
  Endpoint:
  GET https://fapi.binance.com/futures/data/topLongShortAccountRatio

- Top Trader Long/Short Position Ratio:
  Endpoint:
  GET https://fapi.binance.com/futures/data/topLongShortPositionRatio

- Funding / premium context اختياري:
  Endpoint:
  GET https://fapi.binance.com/fapi/v1/premiumIndex

- Exchange info لجلب كل رموز USDT Perpetual:
  Endpoint:
  GET https://fapi.binance.com/fapi/v1/exchangeInfo

ادمج البيانات بالزمن باستخدام nearest/forward-fill timestamp alignment.
لا تجعل اختلاف timestamp يؤدي إلى OI=0 أو L/S=0.
لو البيانات ناقصة، ضع flags وخفّض الثقة بدل كسر التحليل.

============================================================
4) بنية البيانات الداخلية

استخدم dataclasses مثل:

Candle:
timestamp
symbol
open
high
low
close
volume
quote_volume
trades
oi
oi_change
oi_change_pct
oi_value
global_ls
top_account_ls
top_position_ls
rsi

AnalysisFeatures:
dynamic states:
price_move_state
oi_state
trades_state
quote_volume_state
global_ls_state
top_account_ls_state
top_position_ls_state
oi_value_validation
trade_value_validation
data_quality_flags
phase_state
base_detected
reset_detected
trigger_detected
acceptance_state
compression_state
late_crowding_state

AnalysisResult:
symbol
timeframe
data_window
dominant_structural_pattern
structural_bias
readiness_level
signal_timing
cycle_position
price_acceptance
oi_read
oi_value_validation
trades_read
quote_volume_validation
ls_divergence
whale_crowd_read
price_led_reset_ignition_state
price_led_base_ignition_state
price_led_base_vacuum_ignition_state
high_oi_compression_state
trigger_status
post_trigger_acceptance
late_crowding_risk
invalidation_risk
confidence
score
rank_priority
rsi_context_only
final_structural_summary

============================================================
5) Dynamic Baseline Engine

ابنِ DynamicBaselineEngine.

لكل متغير:
price change
range
OI change %
OI absolute level
trades
quote_volume
volume
global_ls_change
top_account_ls_change
top_position_ls_change

احسب:

- rolling median
- MAD أو robust dispersion
- percentile rank داخل النافذة
- robust z-score
- slope آخر N شموع
- acceleration
- retention بعد spike
- local regime state

صنّف كل متغير ديناميكيًا إلى:

Normal
Elevated
Shock
Extreme

لكن التصنيف يجب أن يعتمد على percentiles / robust z-score من نفس العملة، وليس أرقام ثابتة عامة.

مثال:
classify_dynamic(value_series, current_value) -> Normal/Elevated/Shock/Extreme

لا تستخدم threshold ثابت مثل OI > 5%.
استخدم:

- أين يقع التغير الحالي بالنسبة لتوزيع نفس العملة؟
- هل الحدث في أعلى percentile؟
- هل هو أعلى من baseline المحلي؟
- هل استمر أكثر من شمعة؟
- هل حدث بعد Base أو Reset؟

============================================================
6) Data Quality Layer

ابنِ DataQualityChecker يفحص:

- candles count
- missing timestamps
- irregular spacing
- zero/NaN values
- immature RSI في بداية النافذة
- OI يبدأ صغيرًا جدًا ثم يقفز بعنف
- trades عالية جدًا في أول شموع
- L/S يتذبذب بعنف بدون OI واضح
- quote_volume missing
- OI history missing
- L/S history missing

الناتج:
data_quality_flags
confidence_cap
data_reliability_score

إذا أكثر من مشكلة كبيرة:
confidence لا تتجاوز Medium.

============================================================
7) Phase Memory / Window Segmentation

ابنِ PhaseMemoryEngine يقسم النافذة إلى:

background
compression_or_quiet_zone
abnormal_change_zone
pre_ignition_zone
ignition_candle
post_ignition
latest_structure

لا تعتمد على آخر شمعة فقط.

يجب أن يجيب داخليًا:

- هل الحركة الحالية سبقتها بصمة؟
- هل كانت هناك Base؟
- هل كان هناك OI Flush أو Reset؟
- هل OI سبق السعر؟
- هل السعر سبق OI؟
- هل السعر قاد الحركة بعد Reset ثم تبعه OI؟
- هل السعر قاد الحركة من Base بدون Reset ثم تبعه OI؟
- هل السعر قاد الحركة من Base بدون Reset بينما OI بقي ثابتًا أو هبط قليلًا؟
- هل Quote Volume يؤكد Trades؟
- هل Top Position بقي قويًا؟
- هل Top Account يطارد أم لا؟
- هل السعر قريب من البصمة أم بعيد؟

============================================================
8) OI Value Validation

احسب OI Value إذا ممكن:

oi_value = open_interest * close

ثم صنّف:

- OI contracts ↑ + OI Value ↑ = Real Position Expansion
- OI contracts ↑ + OI Value لا يؤكد = Contract-count distortion / Low-price distortion
- OI Value ↑ بسبب السعر فقط وOI ثابت = Price-driven OI Value Expansion
- OI contracts ↓ + OI Value ثابت = price offsets OI decline
- OI contracts ↓ + OI Value ↓ = Real Deleveraging

إذا OI Value غير موثوق أو غير متوفر:
خفّض الثقة ولا تمنع الإشارة.

============================================================
9) Trades / Quote Volume Validation

استخدم number_of_trades و quote_volume من klines.

صنّف:

- Trades ↑ + Quote Volume ↑ = Real Execution Expansion
- Trades ↑ + Quote Volume ضعيف = Micro-trade Noise / Bot Activity
- Trades ضعيفة + Quote Volume ↑ = Large Block-like Execution
- Trades ↑ + Quote Volume ↑ + OI ↑ = Real Capital Activation
- Trades ↑ + Quote Volume ↑ + OI ثابت/هابط = Liquidation / Covering / Spot-led or Vacuum Flow
- Trades ↑ جدًا + السعر لا يتحرك = Absorption Battle

إذا Quote Volume غير متوفر:
لا ترفع confidence إلى High إلا إذا OI والسعر وL/S يؤكدون.

============================================================
10) Price State / Acceptance

ابنِ PriceStructureEngine يصنف:

- healthy uptrend
- explosive up move
- up after reset
- up from base without reset
- sideways/base
- slow downtrend
- violent downtrend
- bounce after drop

وابنِ PriceAcceptanceEngine يصنف:

Accepted Breakout
Constructive Acceptance
Pre-OI Accepted Move After Reset
Pre-OI Accepted Move From Base
Pre-OI / No-OI Accepted Move From Base
Controlled Pullback
Failed Breakout
OI Trap Risk
Structure Invalidated

قبول السعر يجب أن يفحص:

- الإغلاق فوق منطقة trigger
- الحفاظ فوق نصف شمعة trigger
- عدم العودة داخل القاعدة
- عدم كسر قاعدة ما قبل الإشعال
- عدم كسر قاع ما بعد flush

============================================================
11) OI State Engine

صنّف OI إلى:

- gradual OI build
- explosive OI build
- flat OI
- gradual OI decline
- OI Flush
- OI Reload
- Delayed Constructive OI Reload After Reset
- Delayed Constructive OI Reload From Base
- Price-led Base Move Without OI Expansion
- Late OI Expansion
- OI Deleveraging After Pump

لا تعتبر OI الصاعد bullish تلقائيًا.
لا تعتبر OI اللاحق للسعر late تلقائيًا.
السياق هو الحاسم.

============================================================
12) L/S Structure Engine

حلل منفصلًا:

global long/short
top account long/short
top position long/short

استخرج:

- direction
- dynamic change state
- crowd chasing
- account chasing
- top position retention
- top position collapse
- crowd against move
- short pressure
- long crowding

LS Divergence patterns:

Global ↑ + Top Account ↑ + Top Position ↑
Global ↑ + Top Account ↑ + Top Position ↓
Global ↑ + Top Account ↓ + Top Position ↓
Global ↓ + Top Account ↓ + Top Position ثابت أو ↑
Global ↓ + Top Account ↓ + Top Position ↓
Global ↓ + Top Account ↑ + Top Position ↑
Global ثابت + Top Account ↑ + Top Position ↑
Global ثابت + Top Account ↑ + Top Position ↓
Global ↓ جدًا + Top Account ↓ جدًا + Top Position قرب التعادل
Global ↓ + Top Account ↓ + Top Position يبقى Long-heavy لكنه يتراجع
Global ثابت أو ↑ قليلًا + Top Account لا يطارد + Top Position Long-heavy

مهم:
لا تجعل L/S شرطًا قاسيًا مثل:
لا توجد فرصة إلا إذا Global أو Account L/S أقل من 1.

الأصح:

- أقل من 1 = short squeeze fuel قوي
- قريب من 1 وينخفض = squeeze fuel مبكر
- فوق 1 لكنه يهبط بقوة مع Top Position ثابت = ضغط ضد الحركة صالح بشرط trades/quote قوية
- يرتفع مع السعر بعد الحركة = crowding risk / late participation

============================================================
13) Structural Pre-Scanner

قبل القرار النهائي، نفّذ:

OI Flush Detector
Post-Flush Behavior
Pre-Price OI Build-up
Price Leads OI
Ignition Without OI
Price-led Reset Ignition with OI Reload
Price-led Base Ignition without Reset
Price-led Base Vacuum Ignition without OI Expansion
Late OI Crowding
Post-Peak OI Retention
High OI Compression Check
Post-Trigger Acceptance Check
Short Crowding Quality

كل فحص ينتج flags و evidence points وليس قرارًا منفردًا.

============================================================
14) أهم فرع: Price-led Base Vacuum Ignition

هذا الفرع يجب أن يكون واضحًا وقويًا.

لا تسقط العملة بسبب OI ثابت أو هابط قليلًا إذا:

- لا يوجد OI Flush / Reset واضح قبل الحركة
- توجد Base هادئة أو ضغط منخفض قبل الحركة
- السعر خرج من القاعدة قبل OI الكامل
- Trades ارتفعت بوضوح مع أو بعد الخروج
- Quote Volume يؤكد إذا متوفر
- OI ثابت أو هابط قليلًا فقط
- OI لا ينهار بعنف
- Top Position L/S يبقى قويًا أو لا ينهار
- Top Account L/S لا يطارد الصعود بقوة
- Global L/S ليس Long-heavy بشكل مفرط
- السعر يحافظ فوق القاعدة أو فوق نصف شمعة الإشعال

صنّفها كواحد من:
Price-led Base Vacuum Ignition
Price-led Base Ignition without OI Expansion
Vacuum / Stop-driven Base Breakout
Accepted Base Vacuum Ignition

ولا تصنفها Watchlist ضعيف أو Mixed فقط.

============================================================
15) Conflict Resolution

ابنِ ConflictResolver يعطي أولوية للقواعد التالية:

- Post-trigger failure يخفض أي bullish bias.
- Short fuel يلغى إذا السعر يكسر القاعدة.
- OI Flush تلاه ثبات له أولوية على Decay.
- السعر سبق OI بعد Reset ثم OI لحق مع L/S ضد الحركة = Price-led Reset Ignition وليس Late Crowding.
- السعر سبق OI من Base ثم OI لحق مع L/S لا يطارد = Price-led Base Ignition وليس Late Crowding.
- السعر سبق OI من Base وOI لم يلحق لكن Trades/Quote + Top Position + Acceptance تؤكد = Price-led Base Vacuum Ignition.
- السعر سبق OI بدون Reset وبدون Base وL/S أصبح مع الحركة = Late OI Crowding.
- Base Trigger فشل وعاد السعر داخل القاعدة = Failed Base Ignition.
- OI عند قمة النافذة والسعر لا يصنع قمة = risk overlay.
- Trades انفجارية لكن Quote Volume لا يؤكد = bot/noise downgrade.
- OI contracts ↑ لكن OI Value لا يؤكد = OI weight downgrade.
- Funding/Cross-venue غير متوفرين والحالة متضاربة = confidence لا تتجاوز Medium.

============================================================
16) Readiness Level

اختر واحدًا فقط:

Watchlist Only
Primed Structure
Early-Live Structure
Confirmed Trigger
Accepted Structure
Compression / Unresolved
Failed / Invalidated
Late / Risk State

قاعدة:
لا تصنف Early Bullish أو Early-Live إلا إذا readiness أحد:
Primed Structure
Early-Live Structure
Confirmed Trigger قريب من البصمة
Accepted Structure قريب من البصمة

ولا تصنفها مبكرة إذا:
Late / Risk State
Failed / Invalidated
Compression / Unresolved بدون Trigger

استثناء V3.2.1:
يمكن Early-Live أو Confirmed Trigger حتى بدون OI expansion إذا:
Base واضحة + price breakout + trades/quote + OI flat/slightly down + Top Position retention + Top Account non-chasing + price acceptance.

============================================================
17) Dominant Pattern

اختر نمطًا رئيسيًا واحدًا فقط من:

Fresh Long Build-up
Hidden Buildup / Absorption
Absorption After Flush
Short Build Under Stable Price
Short Squeeze / Live Ignition
Vacuum Ignition / Stop-Driven Move
Post-Flush Vacuum Ignition
Late Long Crowding
Post-Pump Crowding Risk
Bull Trap Risk
Long Liquidation / Forced Reset
Liquidity Exit / Decay
Bearish Build-up
Long Trap / Long Punishment
Weak Consolidation
Mixed Structure
Short-Crowded Compression
Failed Squeeze / Squeeze Exhaustion
High OI Neutral Compression
Bot / Noise Expansion
Price-led Reset Ignition with OI Reload
Top-Position Long Retention with Crowd Compression
Price-led Base Ignition without Reset
Failed Base Ignition
Price-led Base Vacuum Ignition without OI Expansion
Failed Base Vacuum Ignition

لا تخرج أكثر من Dominant Pattern واحد.
يمكن وضع secondary evidence في الملخص فقط.

============================================================
18) Structural Bias

اختر واحدًا فقط:

Early Bullish Structure
Early-Live Bullish Structure
Bullish but Event-driven
Bullish but Late
Neutral / Unclear
Neutral-to-Bullish Compression
Distribution Risk
Bearish Structural Risk
Post-Pump Crowding Risk
High Volatility Compression

============================================================
19) Confidence

اختر واحدًا فقط:

High
Medium-High
Medium
Low

High فقط إذا:
OI + OI Value يؤكدان
Trades + Quote Volume يؤكدان
السعر يقبل الحركة
L/S واضح
Readiness = Confirmed Trigger أو Accepted Structure
لا يوجد تعارض كبير
لا يوجد data warmup risk

Medium-High إذا:
Price-led Reset/Base/Vacuum واضح
السعر يقبل
L/S ضد الحركة أو لا يطارد
Top Position لا ينهار
لكن الحركة بدأت قبل OI الكامل أو بدون OI expansion

Medium إذا:
البنية واضحة لكن Quote Volume أو OI Value غير متوفر
أو Readiness = Primed/Early-Live دون Acceptance كامل
أو بعض التعارضات موجودة

Low إذا:
بيانات ضعيفة
Trades بدون قيمة مؤكدة
L/S noisy
OI Value لا يؤكد
السعر بلا قبول
Readiness = Watchlist أو Failed

طبّق confidence cap من Data Quality.

============================================================
20) Scoring and Ranking

ابنِ scoring ديناميكي، ليس أرقامًا ثابتة جامدة.

رتّب النتائج بهذا التسلسل المنطقي:

1. Accepted Structure
2. Confirmed Trigger قريب من البصمة
3. Early-Live Structure
4. Price-led Base Vacuum Ignition قريب من القاعدة
5. Primed Structure
6. Compression / Unresolved
7. Watchlist Only
8. Late / Risk State
9. Failed / Invalidated
10. Avoid / Low Priority

الأولوية ليست لأعلى ارتفاع سعري.
الأولوية للعملات التي تملك:

- بصمة قبل الحركة
- Base أو Reset واضح
- OI أو OI Reload بنّاء
- أو Price-led Base Vacuum صحيح بدون OI expansion
- Trades/Quote Volume حقيقي
- L/S غير مزدحم أو ضد الحركة
- Top Position قوي أو لا ينهار
- Top Account لا يطارد بقوة
- Price Acceptance
- Readiness Level مناسب
- ولم تبتعد كثيرًا عن منطقة البصمة

أضف score رقمي للترتيب، لكن اجعله ناتجًا من evidence dynamic states، وليس threshold ثابت.

============================================================
21) Output Format

لكل عملة في النتائج النهائية اطبع:

Symbol:
Timeframe:
Data Window:
Dominant Structural Pattern:
Structural Bias:
Readiness Level:
Signal Timing:
Cycle Position:
Price Acceptance:
OI Read:
OI Value Validation:
Trades Read:
Quote Volume Validation:
L/S Divergence:
Whale/Crowd Read:
Price-led Reset Ignition State:
Price-led Base Ignition State:
Price-led Base Vacuum Ignition State:
High OI Compression State:
Trigger Status:
Post-Trigger Acceptance:
Late Crowding Risk:
Invalidation / Risk:
Confidence:
Score:
Rank Priority:
RSI Context Only:
Final Structural Summary:

واجعل Console output على شكل جدول مختصر:
rank, symbol, pattern, bias, readiness, confidence, score, risk, summary

ثم احفظ:
scan_results_latest.csv
scan_results_latest.json

داخل OUTPUT_DIR.

============================================================
22) جودة الكود المطلوبة

- استخدم requests, pandas, numpy فقط إن أمكن.
- لو pandas/numpy غير متوفرة، اكتب fallback واضح أو اذكر requirements في أعلى الملف كتعليق.
- اكتب docstrings مختصرة.
- لا تجعل الملف مجرد pseudocode.
- الكود يجب أن يعمل فعليًا.
- أضف main().
- إذا AUTO_RUN=True شغّل scanner مباشرة.
- أضف graceful keyboard interrupt.
- أضف retry/backoff.
- أضف safe float parsing.
- أضف logging بسيط.
- أضف حماية من division by zero.
- أضف handling للرموز التي لا تملك بيانات كافية.
- لا تطبع stack traces طويلة إلا في debug mode.

============================================================
23) اختبار داخلي

بعد كتابة الكود:

- راجع الكود بحثًا عن syntax errors.
- تأكد أن كل function مستخدمة.
- تأكد أن main يعمل.
- تأكد أن scanner لا يتوقف عند فشل رمز واحد.
- تأكد أن النتائج لا تعتمد على السعر وحده.
- تأكد أن RSI لا يدخل في القرار.
- تأكد أن Price-led Base Vacuum Ignition لا يسقط بسبب OI flat/slightly down.
- تأكد أن L/S ليس شرطًا قاسيًا أقل من 1 فقط.
- تأكد أن Quote Volume و OI Value يستخدمان للتحقق لا للإسقاط القاسي.
- تأكد أن output يحتوي كل الحقول المطلوبة.

في النهاية أعطني الكود الكامل فقط داخل ملف واحد، بدون شرح طويل.
