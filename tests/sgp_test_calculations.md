# Weryfikacja poprawności procedury SGP (Schedule Generation Procedure)

Niniejszy dokument przedstawia poglądowe obliczenia stanowiące weryfikację zaimplementowanego silnika symulacyjnego. Wyniki uzyskane z automatycznych testów jednostkowych zostały zestawione z ręcznymi obliczeniami matematycznymi opartymi na modelu z pracy R. Różyckiego, G. Waligóry i J. Węglarza zatytułowanej "Scheduling battery charging jobs with linearly decreasing power
demands to minimize the total time".

Dla wszystkich przypadków testowych przyjęto stałą globalną moc stacji ładowania **$P = 100.0$ kW**. Obliczenia realizowane są w oparciu o trzy równania:
1. Czas przetwarzania zadania **i** (Równanie 7): $d_i = \frac{2 \cdot e_i}{P_{0i}}$
2. Współczynnik spadku poboru mocy dla baterii **i**: $\Delta p_i = \frac{P_{0i}}{d_i}$
3. Czas rozpoczęcia ładowania zadania **j** (Równanie 17): $t_k = \frac{P_{03} - P + \sum_{i \in A_t} P_{0i} + \sum_{i \in A_t} \Delta p_i s_i}{\sum_{i \in A_t} \Delta p_i} = s_j$

---

## Przypadek Testowy 1

### a) Dane
| ID Zadania | Brakująca Energia ($e_i$) | Wymóg Startowy ($P_{0i}$) | Czas Ładowania ($d_i$) | Tempo zwalniania mocy |
| :---: | :---: | :---: | :---: | :---: |
| **B1** | 20.0 kWh | 10.0 kW | 4.00 h | 2.50 kW/h |
| **B2** | 80.0 kWh | 100.0 kW | 1.60 h | 62.50 kW/h |
| **B3** | 45.0 kWh | 67.5 kW | 1.33 h | 50.75 kW/h |

### b) Kluczowe obliczenia
* O czasie $t = 0.00$ h ładowana jest jedynie bateria B1 ($10$ kW). B2 wymaga pełnego wykorzystania akumulatora ($100$ kW), więc czeka na zwolnienie mocy o czasie $t = 4.00$ h.
* O czasie $t = 4.00$ h podłączona zostaje bateria B2. Moment rozpoczęcia ładowania oczekującej baterii B3 wyznaczany jest z przyrostu mocy uwalnianej przez B2:
  $$\Delta t = \frac{P_{03}}{\Delta p_2} = \frac{67.5 \text{ kW}}{62.5 \text{ kW/h}} = 1.08 \text{ h} \implies s_3 = 4.00 + 1.08 = 5.08 \text{ h}$$

### c) Wyniki
* B1 [Start: 0.00 h | Koniec: 4.00 h]
* B2 [Start: 4.00 h | Koniec: 5.60 h]
* B3 [Start: 5.08 h | Koniec: 6.41 h]

**Całkowity czas ładowania (Makespan): 6.41 h**

---

## Przypadek Testowy 2

### a) Dane
| ID Zadania | Brakująca Energia ($e_i$) | Wymóg Startowy ($P_{0i}$) | Czas Ładowania ($d_i$) | Tempo zwalniania mocy |
| :---: | :---: | :---: | :---: | :---: |
| **B1** | 150.0 kWh | 50.0 kW | 6.00 h | 8.33 kW/h |
| **B2** | 100.0 kWh | 50.0 kW | 4.00 h | 12.50 kW/h |
| **B3** | 50.0 kWh | 50.0 kW | 2.00 h | 25.00 kW/h |
| **B4** | 25.0 kWh | 50.0 kW | 1.00 h | 50.00 kW/h |

### b) Kluczowe obliczenia
* O czasie $t = 0.00$ h stacja rozpoczyna ładowanie B1 i B2 ($50 + 50 = 100$ kW).
* Moment podłączenia B3 ($P_{03} = 50.0$ kW) wyliczany jest z równania (17):
  $$t_k = \frac{P_{03} - P + \sum_{i \in A_t} P_{0i} + \sum_{i \in A_t} \Delta p_i s_i}{\sum_{i \in A_t} \Delta p_i} = \frac{50 - 100 + (50 + 50) + 0}{8.33 + 12.50} = \frac{50}{20.833} ≈ 2.40 \text{ h}$$

### c) Wyniki
* B1 [Start: 0.00 h | Koniec: 6.00 h]
* B2 [Start: 0.00 h | Koniec: 4.00 h]
* B3 [Start: 2.40 h | Koniec: 4.40 h]
* B4 [Start: 3.49 h | Koniec: 4.49 h]

**Całkowity czas ładowania (Makespan): 6.00 h**

---

## Przypadek Testowy 3

### a) Dane
| ID Zadania | Brakująca Energia ($e_i$) | Wymóg Startowy ($P_{0i}$) | Czas Ładowania ($d_i$) | Tempo zwalniania mocy |
| :---: | :---: | :---: | :---: | :---: |
| **B1** | 200.0 kWh | 80.0 kW | 5.00 h | 16.00 kW/h |
| **B2** | 5.0 kWh | 25.0 kW | 0.40 h | 62.50 kW/h |
| **B3** | 5.0 kWh | 25.0 kW | 0.40 h | 62.50 kW/h |
| **B4** | 5.0 kWh | 25.0 kW | 0.40 h | 62.50 kW/h |

### b) Kluczowe obliczenia
* B1 zajmuje 80 kW, uniemożliwiając natychmiastowy start B2. Czas oczekiwania na zwolnienie dodatkowych $5$ kW z liniowej charakterystyki B1 wynosi:
  $$t_k = \frac{25 - 100 + 80}{16.00} = \frac{5}{16} = 0.3125 \text{ h} \approx 0.31 \text{ h}$$

* Moment podłączenia B3 ponownie wyliczany jest z równania (17):
$$t_k = \frac{P_{03} - P + P_{01} + (\Delta p_1 \cdot s_1) + P_{02} + (\Delta p_2 \cdot s_2)}{\Delta p_1 + \Delta p_2} = \frac{25 - 100 + 80 + (16 \cdot 0) + 25 + (62.5 \cdot 0.3125)}{16 + 62.5} \approx \mathbf{0.63 \text{ h}}$$
### c) Wyniki
* B1 [Start: 0.00 h | Koniec: 5.00 h]
* B2 [Start: 0.31 h | Koniec: 0.71 h]
* B3 [Start: 0.63 h | Koniec: 1.03 h]
* B4 [Start: 0.88 h | Koniec: 1.28 h]

**Całkowity czas ładowania (Makespan): 5.00 h**

---

## Przypadek Testowy 4

### a) Dane
| ID Zadania | Brakująca Energia ($e_i$) | Wymóg Startowy ($P_{0i}$) | Czas Ładowania ($d_i$) | Tempo zwalniania mocy |
| :---: | :---: | :---: | :---: | :---: |
| **B1** | 60.0 kWh | 60.0 kW | 2.00 h | 30.00 kW/h |
| **B2** | 60.0 kWh | 60.0 kW | 2.00 h | 30.00 kW/h |
| **B3** | 60.0 kWh | 60.0 kW | 2.00 h | 30.00 kW/h |

### b) Wyniki
* B1 [Start: 0.00 h | Koniec: 2.00 h]
* B2 [Start: 0.67 h | Koniec: 2.67 h]
* B3 [Start: 1.67 h | Koniec: 3.67 h]

**Całkowity czas ładowania (Makespan): 3.67 h**

---

## Przypadek Testowy 5

### a) Dane
| ID Zadania | Brakująca Energia ($e_i$) | Wymóg Startowy ($P_{0i}$) | Czas Ładowania ($d_i$) | Tempo zwalniania mocy |
| :---: | :---: | :---: | :---: | :---: |
| **B1** | 10.0 kWh | 90.0 kW | 0.22 h | 405.00 kW/h |
| **B2** | 10.0 kWh | 90.0 kW | 0.22 h | 405.00 kW/h |
| **B3** | 10.0 kWh | 90.0 kW | 0.22 h | 405.00 kW/h |

### b) Wyniki
* B1 [Start: 0.00 h | Koniec: 0.22 h]
* B2 [Start: 0.20 h | Koniec: 0.42 h]
* B3 [Start: 0.40 h | Koniec: 0.62 h]

**Całkowity czas ładowania (Makespan): 0.62 h**

---

## Przypadek Testowy 6

### a) Dane
| ID Zadania | Brakująca Energia ($e_i$) | Wymóg Startowy ($P_{0i}$) | Czas Ładowania ($d_i$) | Tempo zwalniania mocy |
| :---: | :---: | :---: | :---: | :---: |
| **B1–B10** | 100.0 kWh | 10.0 kW | 20.00 h | 0.50 kW/h |
| **B11** | 100.0 kWh | 10.0 kW | 20.00 h | 0.50 kW/h |

### b) Wyniki
* B1–B10 [Start: 0.00 h | Koniec: 20.00 h]
* B11 [Start: 2.00 h | Koniec: 22.00 h]

**Całkowity czas ładowania (Makespan): 22.00 h**

---

## Przypadek Testowy 7

### a) Dane
| ID Zadania | Brakująca Energia ($e_i$) | Wymóg Startowy ($P_{0i}$) | Czas Ładowania ($d_i$) | Tempo zwalniania mocy |
| :---: | :---: | :---: | :---: | :---: |
| **B1** | 50.0 kWh | 50.0 kW | 2.00 h | 25.00 kW/h |
| **B2** | 30.0 kWh | 30.0 kW | 2.00 h | 15.00 kW/h |
| **B3** | 20.0 kWh | 20.0 kW | 2.00 h | 10.00 kW/h |
| **B4** | 50.0 kWh | 50.0 kW | 2.00 h | 25.00 kW/h |

### b) Wyniki
* B1 [Start: 0.00 h | Koniec: 2.00 h]
* B2 [Start: 0.00 h | Koniec: 2.00 h]
* B3 [Start: 0.00 h | Koniec: 2.00 h]
* B4 [Start: 1.00 h | Koniec: 3.00 h]

**Całkowity czas ładowania (Makespan): 3.00 h**

---

## Przypadek Testowy 8

### a) Dane
| ID Zadania | Brakująca Energia ($e_i$) | Wymóg Startowy ($P_{0i}$) | Czas Ładowania ($d_i$) | Tempo zwalniania mocy |
| :---: | :---: | :---: | :---: | :---: |
| **B1** | 100.0 kWh | 100.0 kW | 2.00 h | 50.00 kW/h |
| **B2** | 50.0 kWh | 100.0 kW | 1.00 h | 100.00 kW/h |
| **B3** | 150.0 kWh | 100.0 kW | 3.00 h | 33.33 kW/h |

### b) Wyniki
* B1 [Start: 0.00 h | Koniec: 2.00 h]
* B2 [Start: 2.00 h | Koniec: 3.00 h]
* B3 [Start: 3.00 h | Koniec: 6.00 h]

**Całkowity czas ładowania (Makespan): 6.00 h**

---

## Przypadek Testowy 9

### a) Dane
| ID Zadania | Brakująca Energia ($e_i$) | Wymóg Startowy ($P_{0i}$) | Czas Ładowania ($d_i$) | Tempo zwalniania mocy |
| :---: | :---: | :---: | :---: | :---: |
| **B1** | 10.0 kWh | 20.0 kW | 1.00 h | 20.00 kW/h |
| **B2** | 20.0 kWh | 40.0 kW | 1.00 h | 40.00 kW/h |
| **B3** | 30.0 kWh | 60.0 kW | 1.00 h | 60.00 kW/h |
| **B4** | 40.0 kWh | 80.0 kW | 1.00 h | 80.00 kW/h |

### b) Wyniki
* B1 [Start: 0.00 h | Koniec: 1.00 h]
* B2 [Start: 0.00 h | Koniec: 1.00 h]
* B3 [Start: 0.33 h | Koniec: 1.33 h]
* B4 [Start: 1.00 h | Koniec: 2.00 h]

**Całkowity czas ładowania (Makespan): 2.00 h**

---

## Przypadek Testowy 10

### a) Dane
| ID Zadania | Brakująca Energia ($e_i$) | Wymóg Startowy ($P_{0i}$) | Czas Ładowania ($d_i$) | Tempo zwalniania mocy |
| :---: | :---: | :---: | :---: | :---: |
| **B1** | 40.0 kWh | 80.0 kW | 1.00 h | 80.00 kW/h |
| **B2** | 30.0 kWh | 60.0 kW | 1.00 h | 60.00 kW/h |
| **B3** | 20.0 kWh | 40.0 kW | 1.00 h | 40.00 kW/h |
| **B4** | 10.0 kWh | 20.0 kW | 1.00 h | 20.00 kW/h |

### b) Wyniki
* B1 [Start: 0.00 h | Koniec: 1.00 h]
* B2 [Start: 0.50 h | Koniec: 1.50 h]
* B3 [Start: 0.79 h | Koniec: 1.79 h]
* B4 [Start: 0.90 h | Koniec: 1.90 h]

**Całkowity czas ładowania (Makespan): 1.90 h**