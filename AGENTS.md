# Instrukcje Projektowe (Kilo Code)

Projekt pytigon-lib jest częścią większego projektu Pytigon napisany jest głównie w python, korzysta z Django. Szablony django zostały zastąpione przez szablony .ihtml. Cechą harakterystyczną tych szablonów jest to, że bazują na wcięciach kodu i są kompilowane do szablonów django.

Projekt Pytigon składa się z kilku części:
1. pytigon_lib (wnętrze projektu pytigon-lib), biblioteki pomocnicze system
2. pytigon - główna część systemu pytigon
3. pytigon_gui - gui do systemu Pytigon (wnętrze projektu pytigon-gui)
4. pytigon_standard_prj - przykładowe projekty systemu Pytigon (wnętrze projektu pytigon-standard-prj)
5. doc - dokumentacja systemu Pytigon
6. frontend - frontend systemu Pytigon, głównie pliki .sass dla css oraz .py kompilowane za pomocą pscript do plików .js

# Uruchamianie i testy
Projekt pytigon nie korzysta bezpośrednio z interpretera Python ale za pośrednictwem programu ptig. Aby uruchomić jakiś przykładowy projekt z folderu pytigon_standard_prj/prj należy użyć polecenia:
ptig manage_[[nazwa_projektu]] runserver
Aby uruchomić python użyj:
ptig python [[parametry]]

WAŻNE: Do wszelkich wywołań interpretera Pythona używaj "ptig python", a nie gołego "python", także przy szybkich sprawdzeniach i importach (np. "ptig python -c 'import mcp'"). Środowisko ptig może mieć inny (większy) zestaw zależności niż bazowy interpreter — pakiet dostępny w ptig może być niedostępny w gołym python, i odwrotnie. Sprawdzenie wersji pakietu: "ptig python -m pip show [[pakiet]]" lub "ptig python -m pip list".

Aby uruchomić testy użyj polecenia:
ptig -m pytest lub ptig @pytest (@ zastępuje -m)
Testy uruchamiaj zawsze z katalogu głównego repozytorium jedną komendą (np. "ptig @pytest tests/"), aby uniknąć rozjazdów konfiguracji pytest między pyproject.toml a plikami pytest.ini w podkatalogach.


## Architektura i Zasady


* Zwróć uwagę na shell, w którym będziesz pracował. Może się okazać że działasz w xonsh a nie bash.
