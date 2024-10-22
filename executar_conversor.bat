@echo off
cd /d "C:\Users\AndreGarcia\Desktop\NtoD\img2img-turbo"

REM Verifica se o ambiente virtual está ativo
if not defined VIRTUAL_ENV (
    REM Se não estiver ativo, tenta ativar
    if exist "novo_ambiente\Scripts\activate.bat" (
        call "novo_ambiente\Scripts\activate.bat"
    ) else (
        echo Ambiente virtual nao encontrado. Por favor, crie o ambiente manualmente.
        pause
        exit /b 1
    )
)

REM Executa o script Python
python ambient.py

REM Mantém a janela aberta em caso de erro
if %errorlevel% neq 0 pause

REM Desativa o ambiente virtual
call deactivate
