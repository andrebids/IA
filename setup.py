import subprocess
import sys
import os
import json
import tkinter as tk
from tkinter import messagebox

def verificar_requisitos():
    """Verifica se todos os requisitos estão instalados"""
    with open('versoes_ambiente.json', 'r') as f:
        versoes = json.load(f)
    
    return versoes

def criar_ambiente_virtual():
    """Cria um ambiente virtual Python"""
    try:
        subprocess.check_call([sys.executable, "-m", "venv", "novo_ambiente"])
        return True
    except:
        return False

def instalar_dependencias(versoes):
    """Instala todas as dependências com versões específicas"""
    python_path = os.path.join("novo_ambiente", "Scripts", "python.exe")
    pip_path = os.path.join("novo_ambiente", "Scripts", "pip.exe")
    
    pacotes_principais = [
        f"torch=={versoes['pacotes']['torch']}",
        f"diffusers=={versoes['pacotes']['diffusers']}",
        f"huggingface-hub=={versoes['pacotes']['huggingface-hub']}",
        f"transformers=={versoes['pacotes']['transformers']}",
        f"accelerate=={versoes['pacotes']['accelerate']}"
    ]
    
    for pacote in pacotes_principais:
        try:
            subprocess.check_call([pip_path, "install", pacote])
            messagebox.showinfo("Progresso", f"Instalado: {pacote}")
        except:
            messagebox.showerror("Erro", f"Falha ao instalar {pacote}")

def configurar_ambiente():
    """Função principal de configuração"""
    root = tk.Tk()
    root.withdraw()
    
    try:
        versoes = verificar_requisitos()
        
        if not criar_ambiente_virtual():
            messagebox.showerror("Erro", "Falha ao criar ambiente virtual")
            return
        
        messagebox.showinfo("Progresso", "Ambiente virtual criado com sucesso")
        instalar_dependencias(versoes)
        
        messagebox.showinfo("Sucesso", "Ambiente configurado com sucesso!")
    except Exception as e:
        messagebox.showerror("Erro", f"Erro durante a configuração: {str(e)}")

if __name__ == "__main__":
    configurar_ambiente()