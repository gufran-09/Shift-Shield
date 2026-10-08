# ShiftShield: Field Interviews & Test Observations

**Conducted by**: Gufran (Cloud & Product)  
**Location**: Campus Construction & Concrete Yard Facility (Hyderabad / Cyberabad cluster)  
**Date**: October 7–8, 2026

---

## 1. Supervisor Interview

- **Role**: Site Foreman / Civil Contractor (Site Supervisor)
- **Worksite**: Active commercial exterior framing and masonry yard (~22 workers)
- **Key Questions & Responses**:
  - *Q: What do you do when a government heatwave SMS arrives?*  
    > *"We get the generic SMS from disaster management saying 'Heatwave Alert: Stay indoors from 12 to 3 PM'. But we have deadlines. If we stop all work for three hours every afternoon, the contractor deducts wages or penalties. Nobody tells us how much to rest at 10 AM when the sun is already roasting us."*
  - *Q: Who decides breaks on site?*  
    > *"I do, based on how people look and whether cement is curing too fast. But if an app gave an official table telling me: 'At 32 °C WBGT, 30 min work / 30 min rest in shade', I can justify that to my client."*
  - *Q: What phone and language do you use?*  
    > *"Android smartphone (Redmi). Hindi and Telugu primarily."*
  - *Q: Would you tap a button to confirm breaks started?*  
    > *"Yes, one tap on a link or phone is easy. A long form or login with password would never get used during work."*

---

## 2. Worker Interviews

- **Worker 1 (Mason, 34 years)**:
  - *Phone*: Feature smartphone (WhatsApp-enabled).
  - *Quote*: *"If a poster or QR code is on the water drum, I can scan it during my rest. But I will not put my name or phone number. If the contractor sees my name complaining about no break, I won't get hired tomorrow."*
  - *Implication for ShiftShield*: **Strict anonymity**. Zero names, zero phone numbers, zero cookies or device identifiers stored. Response split hidden until at least 3 workers submit.

- **Worker 2 (Material Handler, 28 years)**:
  - *Language*: Telugu / Hindi.
  - *Quote*: *"Just give two big buttons: 'We got break' and 'No break'. And a button if anyone feels dizzy. Drinking water must be cold and under a shade tarpaulin."*
  - *Implication for ShiftShield*: Thumb-first buttons with high visual contrast, local language text, and optional symptom check that can only tighten the schedule.

---

## 3. Field Usability Check & QR Test

- **Test Scenario**: 3 test workers scanning `/rest/concrete-yard` on mobile 4G/5G.
- **Observations**:
  - Load time on 4G mobile browser: **< 1.2 seconds**.
  - No app install or login barrier: All 3 participants completed the break check in **under 8 seconds**.
  - Aggregation verification: First 2 submissions kept the yes/no split masked; 3rd submission revealed the aggregate breakdown without exposing individual timestamps.
  - Symptom reporting: Selected "Dizziness" triggered the symptom counter, elevating the site floor safely without exposing who clicked it.
