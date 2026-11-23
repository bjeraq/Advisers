# Dossier 17: Rule of 72
Researched 23 Nov 2026. This is information, not advice.

## Safe to say on air (2 sources)
- **Formula:** years to double ≈ 72 ÷ annual return (%). The exact answer is ln(2) ÷ ln(1 + r).
  - https://www.wikipedia.com/wiki/Rule_of_72
  - https://wealthsimple.com/en-ca/learn/rule-of-72-definition-formula
- **Accuracy table** (computed with python; math, not sourced):

| Rate | 72 ÷ r | Exact (annual compounding) |
|---|---|---|
| 3% | 24.0 y | 23.45 y |
| 6% | 12.0 y | 11.90 y |
| 8% | 9.0 y | 9.01 y |
| 10% | 7.2 y | 7.27 y |
| 12% | 6.0 y | 6.12 y |

  - The rule is most accurate around 6–10% and best near 8%. It overstates the time at low rates and understates it at high rates.
- **Origin:** the first known written appearance is in Luca Pacioli's *Summa de arithmetica*, Venice, 1494. Pacioli gives the rule without deriving it, so it probably predates him.
  - https://www.wikipedia.com/wiki/Rule_of_72
  - https://mathshistory.st-andrews.ac.uk/Extras/Pacioli_logarithm/
  - https://en.wikipedia.com/wiki/Summa_de_arithmetica
- **Flip side (inflation):** at 3% inflation prices double in 72 ÷ 3 = 24 years, so purchasing power halves. The exact figure is ln2 ÷ ln1.03 = 23.45 years (math).
- **Kuwait inflation, latest found: about 2.2% y/y (July 2026, CSB).**
  - Earlier 2026 readings: Feb 1.92%, Apr 2.57%, May 2.49%.
  - https://www.agbi.com/analysis/economy/2026/10/gulf-living-costs-higher-but-inflation-stays-modest/
  - https://tradingeconomics.com/kuwait/inflation-cpi
  - May figure: https://www.aljarida.com/article/135252
  - At 2.2%, prices double in about 32 years (72 ÷ 2.2 = 32.7; exact 31.9).
  - CSB figures for Aug–Oct 2026 were not found. Say "around 2%" or "2.2% in July."
- **CBK discount rate: 3.50%.** Cut to this level effective 11 Dec 2025, then held, including at the 17 Sep 2026 meeting.
  - https://www.cbk.gov.kw/en/cbk-news/announcements-and-press-releases/press-releases/2025/12/202512101500-cbk-cuts-the-discount-rate-by-25-basis-points-to-350
  - https://www.aljarida.com/article/144766
  - https://tradingeconomics.com/kuwait/interest-rate

## Single source: do not say on air (illustration with an "approx." label only)
- **Typical KD deposit rates, 2026:**
  - CBK published averages, Feb 2026, for local conventional banks (excludes Islamic banks): 12-month KD time deposit about 4.18%, 6-month about 4.02%, 1-month about 3.58%. https://www.cbk.gov.kw/ar/statistics-and-publication/dynamic-statistical-releases/monthly/2026/02/20 (read via search extract)
  - A different series, average household 1-year deposit rate: 3.6% (Jun 2026). https://www.theglobaleconomy.com/Kuwait/deposit_interest_rate/
  - The two figures are not the same measure. Use a round "around 4%" in the example and label it illustrative.
- The claim that Pacioli's rule sits on fol. 181, n. 44 appears in only one source.

## Worked Kuwait example (math on an illustrative rate)
- A deposit at about 4% doubles in 72 ÷ 4 = 18 years (exact 17.7).
  - At 4.18%: 17.2 by the rule, 16.9 exact.
- After about 2.2% inflation, the **real** gain is about 1.9–2% a year (exact (1.0418 / 1.0219) − 1 ≈ 1.95%). On that basis, real purchasing power doubles in about 36 years.
- Script line: "Your deposit doubles in about 18 years, but prices double too, in about 32 years at today's inflation."

## Uncertainties
- No CSB release for Aug–Oct 2026 was found. Check csb.gov.kw before air.
- Deposit rates differ by bank, amount and tenor. Islamic banks quote expected profit rates, not interest. Name no bank.
