@echo off
REM Script d'indexation hebdomadaire automatique
REM À exécuter chaque lundi matin par exemple

echo ========================================
echo   INDEXATION HEBDOMADAIRE DES MTs
echo ========================================
echo.

REM Dossier contenant vos nouveaux MTs de la semaine
REM Modifiez ce chemin selon votre organisation
set DOCS_FOLDER=C:\Users\David\Documents\MTs

echo Indexation de: %DOCS_FOLDER%
echo.

REM Lancer l'indexation
python indexer.py "%DOCS_FOLDER%"

echo.
echo ========================================
echo   INDEXATION TERMINÉE
echo ========================================
echo.

REM Optionnel: Ouvrir l'interface web après indexation
echo Voulez-vous lancer l'interface web? (O/N)
set /p LAUNCH_WEB=

if /i "%LAUNCH_WEB%"=="O" (
    echo Lancement de l'interface web...
    streamlit run app.py
)

pause
