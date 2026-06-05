# Can
ماسح العملات 
أنت تعمل على مشروع Python لتحليل Binance Futures وفق منهجية:

Structural Liquidity Discovery Tree V3.2.1-O

الملف الأساسي للكود:
"2_v321_operational_v321o_patch1.py"

المطلوب:
بناء نظام Backtest/Audit عملي يختبر هل الكود يكتشف العملات قبل الارتفاع الحقيقي، ثم إذا فشل في بعض الحالات، يستخرج السبب الجذري ويطبق تصحيحات محافظة لا تكسر منطق الشجرة، ثم يعيد الاختبار حتى الوصول إلى أفضل دقة ممكنة، مع استهداف Precision/Recall/Success Rate لا يقل عن 90% على بيانات تحقق خارجية إن كان ذلك واقعيًا.

مهم جدًا:
لا تغيّر جوهر الشجرة لتحسين النتائج شكليًا.
لا تستخدم lookahead داخل لحظة الإشارة.
لا تجعل الكود يعرف المستقبل أثناء التصنيف.
لا تعتبر الوصول إلى 90% نجاحًا إذا كان بسبب overfitting.
إذا لم يمكن الوصول إلى 90% بدون كسر المنهجية أو بسبب نقص البيانات، اذكر ذلك بوضوح وقدم أعلى نتيجة موثوقة.

============================================================

1) افهم الكود الحالي
   ============================================================

اقرأ الملف:
"2_v321_operational_v321o_patch1.py"

استخرج منه:

- محرك V3.2.1-O
- دوال التحليل
- PatternCandidate / Candidate Eligibility إن وجدت
- Readiness
- Confidence
- Base Vacuum logic
- Price-led Base Ignition
- Price-led Reset Ignition
- Conflict Rules
- Final output

لا تحذف المنطق الحالي.
التعديلات يجب أن تكون patches محافظة ومفهومة.

============================================================
2) ابنِ Backtest Harness مستقل

أنشئ ملفًا جديدًا:

"backtest_v321o_uploaded_cases.py"

وظيفته:

- قراءة جميع ملفات العملات المرفوعة بصيغة ".txt" أو ".doc" أو ".csv" إن وجدت.
- استخراج الجدول النصي الموجود في ملفات Binance Futures merged data.
- تحويل كل صف إلى Candle compatible مع الكود الحالي.
- التعامل مع نقص Quote Volume إن لم يكن موجودًا في الجدول.
- تمرير البيانات زمنيًا candle-by-candle.
- عند كل شمعة، استدعِ محرك التحليل فقط باستخدام البيانات المتاحة حتى تلك الشمعة.
- سجّل أول إشارة قبل الارتفاع، لا بعده فقط.

يجب دعم الحقول التالية إن وجدت:

- Time
- Symbol
- Close
- RSI
- Trades
- OI
- OI Chg
- OI Chg %
- Account L/S
- Position L/S
- Global L/S
- Volume
- Quote Volume

إذا لم يوجد Volume أو Quote Volume:

- لا تسقط الإشارة تلقائيًا.
- ضع "quote_volume_available=False"
- اجعل Confidence cap = Medium فقط.
- لا تعتبر Micro-trade Noise إلا إذا كان Quote Volume موجودًا فعلًا ويخالف Trades.

============================================================
3) تعريف الارتفاع الحقيقي Event Labeling

أضف نظام labeling قابل للتعديل.

المعايير الافتراضية:

Major Rise Event:

- future_return_max خلال 4 إلى 24 شمعة >= 12%
  أو
- future_return_max خلال 4 إلى 16 شمعة >= 8% مع Trades expansion واضح
  أو
- السعر حقق أعلى قمة مستقبلية معتبرة داخل النافذة بعد Base/Trigger

أضف إعدادات CLI:

- "--rise-threshold 0.12"
- "--min-lead-bars 1"
- "--max-lookahead-bars 24"
- "--max-adverse-before-rise 0.06"
- "--accepted-patterns early_watch|strict_live"

احسب لكل شمعة:

- future_max_return
- future_max_time
- adverse_move_before_future_max
- bars_to_future_max

ممنوع استخدام هذه القيم داخل محرك التصنيف.
تستخدم فقط لتقييم الإشارة بعد إخراجها.

============================================================
4) تعريف نجاح الاكتشاف

الإشارة تعتبر ناجحة إذا:

- ظهرت قبل أو عند بداية الحركة، وليس بعد الامتداد الكبير.

- Readiness واحد من:
  
  - Primed Structure
  - Early-Live Structure
  - Confirmed Trigger
  - Accepted Structure قريب من البصمة

- Structural Bias واحد من:
  
  - Early Bullish Structure
  - Early-Live Bullish Structure
  - Bullish but Event-driven
  - Neutral-to-Bullish Compression

- النمط ليس:
  
  - Late Long Crowding
  - Post-Pump Crowding Risk
  - Failed / Invalidated
  - Bearish Structural Risk
  - Distribution Risk

- future_max_return >= rise_threshold

- adverse_move_before_rise <= max_adverse_before_rise

- signal_time قبل future_max_time بعدد شموع مناسب

قسّم النتائج إلى:

A) Early Success:
الإشارة ظهرت قبل الانفجار بمدة >= min_lead_bars.

B) Live Success:
الإشارة ظهرت في أول شمعة Trigger أو أول شمعة Acceptance.

C) Late Detection:
الكود اكتشف العملة بعد ارتفاع كبير.

D) Missed Opportunity:
حدث ارتفاع حقيقي ولم تظهر أي إشارة مناسبة قبله.

E) False Positive:
ظهرت إشارة مناسبة لكن لم يحدث ارتفاع كافٍ بعدها.

============================================================
5) أوضاع الاختبار

نفّذ وضعين:

1) early_watch
   يقبل:

- Primed Structure
- Early-Live Structure
- Confirmed Trigger
- Accepted Structure

الهدف:
اكتشاف مبكر جدًا قبل الحركة، مع تحمل False Positives أكثر.

2) strict_live
   يقبل:

- Early-Live Structure
- Confirmed Trigger
- Accepted Structure

الهدف:
دقة أعلى، لكن إشارات أقل وربما تأخر بسيط.

اعرض النتائج لكل وضع بشكل منفصل.

============================================================
6) التقارير المطلوبة

أنشئ مجلد:

"backtest_reports_v321o/"

واكتب الملفات التالية:

1. "summary.json"
   يتضمن:

- total_symbols
- total_events
- detected_events
- missed_events
- false_positives
- early_success_count
- live_success_count
- late_detection_count
- precision
- recall
- f1
- success_rate
- average_lead_bars
- median_lead_bars
- average_future_return_after_signal
- average_adverse_move_before_rise

2. "per_symbol_report.csv"
   الأعمدة:

- symbol
- file
- event_start_time
- event_peak_time
- event_peak_return
- first_signal_time
- first_signal_price
- first_signal_pattern
- first_signal_bias
- first_signal_readiness
- first_signal_confidence
- lead_bars
- max_future_return_after_signal
- max_adverse_before_rise
- result_class
- failure_reason

3. "missed_cases.json"
   لكل حالة فشل:

- symbol
- time_range
- what_happened
- expected_pattern
- actual_pattern
- actual_readiness
- why_missed
- suggested_fix
- patch_applied true/false

4. "candidate_timeline_<SYMBOL>.csv"
   لكل عملة:

- كل شمعة
- close
- trades
- oi
- oi_change_pct
- ls values
- detected pattern
- readiness
- confidence
- future_max_return
- result tag

============================================================
7) Root Cause Analysis عند الفشل

إذا فشل الكود في اكتشاف عملة قبل الارتفاع، صنّف السبب بدقة ضمن هذه الفئات:

- BASE_NOT_DETECTED
- BASE_DETECTED_BUT_LOW_QUALITY
- PRICE_LED_MOVE_CLASSIFIED_MIXED
- QUOTE_VOLUME_MISSING_DOWNGRADED_TOO_HARD
- OI_FLAT_DOWN_REJECTED_WRONGLY
- TOP_POSITION_RETENTION_TOO_STRICT
- TOP_ACCOUNT_NON_CHASE_TOO_STRICT
- GLOBAL_LONG_HEAVY_FILTER_TOO_STRICT
- DELAYED_OI_RELOAD_NOT_RECOGNIZED
- TRIGGER_DETECTED_TOO_LATE
- ACCEPTANCE_TOO_STRICT
- LATE_RISK_OVERRIDE_TOO_AGGRESSIVE
- MICRO_TRADE_NOISE_FALSE_POSITIVE
- DATA_PARSING_LOSS
- LOOKBACK_WINDOW_TOO_SHORT
- TRUE_NEGATIVE_NOT_A_VALID_SETUP

لكل سبب:

- أعط مثالًا من البيانات.
- اذكر الشمعة التي كان يجب التقاطها.
- اذكر الشرط الذي منع التصنيف.
- اقترح تعديلًا محددًا.

============================================================
8) قواعد التصحيح المسموح بها

مسموح بتعديل الكود فقط إذا كان التعديل يحافظ على منطق V3.2.1-O.

تصحيحات مسموحة:

- جعل thresholds ديناميكية بدل ثابتة.
- تحسين Base Quality.
- تحسين near_footprint.
- تحسين trigger_index و oi_reload_index.
- عدم إلغاء Base Vacuum عند Quote Volume missing.
- تحويل missing Quote Volume إلى confidence cap وليس rejection.
- جعل Top Position Retention percentile-based.
- جعل Top Account non-chase dynamic.
- فصل Global long-heavy الحقيقي عن Global normal-high.
- منع Base Vacuum فقط إذا هناك crowd chase واضح أو top position collapse.
- تحسين delayed OI reload خلال 1 إلى 2 شمعة بعد Trigger.
- إضافة event_timeline داخل Phase Memory.
- تحسين ترتيب Pattern Priority عند التعارض.

تصحيحات ممنوعة:

- استخدام المستقبل داخل التصنيف.
- جعل كل pump يتحول إلى إشارة صحيحة بعد معرفته.
- حذف Conflict Rules.
- حذف Late Risk.
- حذف Failed/Invalidated.
- رفع كل Mixed إلى Bullish.
- جعل RSI عامل قرار.
- خفض شروط Base Vacuum لدرجة التقاط أي قفزة سعرية.
- تغيير جوهر الشجرة لتحقيق 90% وهمية.

============================================================
9) Patch Loop

نفّذ حلقة تحسين بحد أقصى 5 جولات.

في كل جولة:

1. شغّل backtest.
2. احسب المقاييس.
3. استخرج missed cases و false positives.
4. حدد أعلى 3 أسباب فشل تكرارًا.
5. طبق patch محافظ.
6. أعد الاختبار.
7. قارن النتائج قبل/بعد.
8. إذا تحسنت الدقة بدون ارتفاع كبير في false positives، احتفظ بالتعديل.
9. إذا التعديل سبب overfitting أو كسر حالات أخرى، تراجع عنه.

لا تقبل أي patch إلا إذا:

- يحسن recall أو precision بوضوح.
- لا يخفض precision بقوة.
- لا يحول Late/Risk إلى Early بالخطأ.
- لا يكسر self-test.
- لا يكسر audit.

============================================================
10) معيار الوصول إلى 90%

استهدف:

early_watch:

- recall >= 0.90 على أحداث الارتفاع الحقيقية
- precision >= 0.70 على الأقل
- average lead bars >= 1

strict_live:

- precision >= 0.90
- recall قدر الإمكان، ويفضل >= 0.75

إذا كانت العينة كلها عملات ارتفعت فقط، فلا تحسب precision الحقيقي إلا إذا أضفت negative samples.
في هذه الحالة:

- احسب detection_rate على العملات المرتفعة
- واذكر أن precision يحتاج عملات لم ترتفع لاختباره.

إذا لم توجد negative samples، أنشئ تحذيرًا في التقرير:
"Precision is not reliable without non-rising control symbols."

============================================================
11) اختبارات إلزامية بعد كل تعديل

شغّل:

python3 -m py_compile 2_v321_operational_v321o_patch1.py
python3 2_v321_operational_v321o_patch1.py --audit
python3 2_v321_operational_v321o_patch1.py --self-test
python3 backtest_v321o_uploaded_cases.py --input-dir . --mode early_watch
python3 backtest_v321o_uploaded_cases.py --input-dir . --mode strict_live

إذا تغير اسم الملف بعد patch، استخدم الاسم الجديد وحدث الأوامر.

============================================================
12) المخرجات النهائية المطلوبة

في نهاية العمل، اعرض:

1. ملخص النتائج قبل التعديلات.
2. ملخص النتائج بعد كل Patch.
3. أعلى أسباب الفشل.
4. التعديلات التي تم تطبيقها.
5. التعديلات التي تم رفضها ولماذا.
6. هل وصلنا إلى 90% أم لا؟
7. إذا وصلنا: هل النتيجة موثوقة أم overfit؟
8. إذا لم نصل: ما السبب؟
9. الملفات التي تم إنشاؤها أو تعديلها.

واكتب في النهاية:

- أفضل نسخة للكود.
- أفضل mode للاستخدام الحي:
  - early_watch
  - strict_live
- توصية تشغيل:
  - أي Readiness تظهر في التنبيه.
  - أي Readiness تظهر فقط في المراقبة.
  - أي patterns يجب استبعادها من التنبيه.

============================================================
13) تحذير صارم: لا تطارد 90% بأي ثمن

هدف 90% ليس رقمًا شكليًا. المطلوب هو 90% موثوقة قابلة للعمل في السوق الحي، وليس 90% ناتجة عن overfitting على الملفات المرفوعة فقط.

ممنوع تمامًا:

- تعديل الشروط حتى تنجح فقط على العملات المرفوعة.
- استخدام المستقبل داخل التصنيف.
- جعل كل Pump تاريخي يتحول إلى إشارة صحيحة.
- تحويل Mixed Structure إلى Bullish فقط لأنه سبق ارتفاعًا.
- حذف Late / Risk أو Failed / Invalidated لتجميل النتائج.
- تخفيف Base Vacuum حتى يلتقط أي شمعة صاعدة.
- استخدام RSI كعامل قرار.
- رفع الثقة إلى High عند نقص Quote Volume أو OI Value.
- قبول Patch يحسن recall لكنه يدمّر precision.
- قبول Patch يجعل الكود متفائلًا دائمًا.

القاعدة:
إذا لم يمكن الوصول إلى 90% بدون كسر منطق V3.2.1-O، اذكر ذلك صراحة.

المطلوب عند عدم الوصول إلى 90%:

- أعطني أعلى نتيجة موثوقة.
- اشرح لماذا لم نصل إلى 90%.
- هل السبب نقص بيانات؟
- هل السبب عينة صغيرة؟
- هل السبب عدم وجود negative samples؟
- هل السبب أن بعض الحركات كانت Price-only pump أو News/Event-driven؟
- هل السبب أن Quote Volume أو OI Value غير موجود في الملفات؟
- هل السبب أن الشجرة محافظة بطبيعتها؟

يجب التفريق بين:

1. Detection Rate على العملات التي ارتفعت فقط.
2. Precision حقيقي يحتاج عملات لم ترتفع أيضًا.
3. Recall على أحداث الارتفاع.
4. Live usability في السوق الحقيقي.

إذا كانت الملفات المرفوعة كلها لعملات ارتفعت، فلا تدّعِ أن precision = 90%.
اكتب بوضوح:
"Precision is not reliable without non-rising control symbols."

أي Patch يجب أن يمر عبر:

- self-test
- audit
- backtest
- comparison before/after
- false positive check إن وجدت negative samples

لا تقبل Patch إلا إذا:

- يحسن النتيجة عبر أكثر من عملة.
- لا يعتمد على اسم عملة محددة.
- لا يعتمد على وقت محدد.
- لا يستخدم future data.
- لا يلغي قواعد المخاطر.
- لا يحول الإشارات المتأخرة إلى مبكرة بلا سبب بنيوي.

في نهاية العمل، اعطني حكمًا صريحًا:

- هل وصلنا إلى 90% موثوقة؟ نعم/لا.
- إذا نعم: ما الدليل؟
- إذا لا: ما أعلى نتيجة موثوقة؟
- ما التعديلات التي حسّنت الأداء؟
- ما التعديلات التي رفضتها لأنها overfitting؟
- ما البيانات الإضافية المطلوبة للوصول إلى تقييم أدق؟
ابدأ الآن بإنشاء backtest harness وتشغيل الاختبارات على الملفات الموجودة في المجلد الحالي.
الهدف ليس جعل النتائج تبدو ممتازة على الماضي، بل بناء كود يلتقط الاستعداد الحقيقي قبل الارتفاع في السوق الحي مع أقل قدر ممكن من الإشارات الكاذبة.
