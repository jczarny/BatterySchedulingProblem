W ramach niniejszej pracy zaimplementowano w języku Python szereg rozwiązań i algorytmów, których kod źródłowy udostępniono w niniejszym repozytorium. Struktura projektu obejmuje następujące elementy:

* **katalog `models`** - przechowuje definicje baterii oraz stacji ładującej, w tym logikę odpowiedzialną za przetwarzanie zadań i wyliczanie funkcji celu (*makespan*);
* **katalog `schedulers`** - zawiera algorytmy szeregujące, w tym metaheurystyki, rozwiązania zachłanne oraz algorytm przeglądu pełnego (*brute force*);
* **katalog `tests`** - zbiór testów jednostkowych dla procedury wyliczania funkcji celu, popartych ręcznymi obliczeniami weryfikującymi poprawność modelu; 
* **katalog `optimizer_results`** - zbiór plików tekstowych przechowujących wyniki ze strojenia algorytmów; 
* **`optimizer.py`** - klasa wykorzystywana do ewaluacji konfiguracji dla poszczególnych algorytmów metaheurystycznych;
* **`instance_generator.py`** - moduł zawierający definicję generatora instancji testowych;
* **`TODO: main.py`** - główny skrypt sterujący, pozwalający na uruchomienie poszczególnych eksperymentów;
* **`TODO: Jupyter notebook`** - projekt wykonany w narzędziu Jupyter Notebook, odpowiedzialny za wygenerowanie ostatecznej analizy porównawczej algorytmów szeregujących.

---
> **TODO:** Do dalszego uzupełnienia w przyszłości.
