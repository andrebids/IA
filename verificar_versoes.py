import pkg_resources
import sys
import json
import subprocess
from tkinter import messagebox

def obter_versoes_necessarias():
    """Define as versões específicas necessárias para o projeto"""
    return {
        'python': '3.10.6',
        'pacotes': {
            'torch': '2.0.1',
            'torchvision': '0.15.2',
            'diffusers': '0.25.1',
            'huggingface-hub': '0.25.2',
            'transformers': '4.30.2',
            'accelerate': '0.20.3',
            'wandb': 'latest',
            'pillow': 'latest',
            'tqdm': 'latest',
            'numpy': 'latest'
        }
    }

def obter_versoes_instaladas():
    """Obtém as versões atualmente instaladas"""
    pacotes = {}
    for pacote in pkg_resources.working_set:
        pacotes[pacote.key] = pacote.version
    return {
        'python': sys.version.split()[0],
        'pacotes': pacotes
    }
def get_valid_size(size):
    """Ajusta o tamanho para ser múltiplo de 8"""
    return (size // 8) * 8

def build_transform(img_prep):
    """Constrói a transformação para as imagens"""
    if img_prep == "resize256":
        size = get_valid_size(256)
        return transforms.Compose([
            transforms.Resize(size, interpolation=transforms.InterpolationMode.LANCZOS),
            transforms.CenterCrop(size)
        ])
    elif img_prep == "resize512":
        size = get_valid_size(512)
        return transforms.Compose([
            transforms.Resize(size, interpolation=transforms.InterpolationMode.LANCZOS),
            transforms.CenterCrop(size)
        ])
    else:
        raise ValueError(f"Preparação de imagem desconhecida: {img_prep}")
def verificar_e_instalar():
    """Verifica e instala as versões necessárias"""
    versoes_necessarias = obter_versoes_necessarias()
    versoes_instaladas = obter_versoes_instaladas()
    
    # Verifica Python
    if not versoes_instaladas['python'].startswith('3.10'):
        messagebox.showwarning("Aviso", "Versão do Python incorreta. É necessário Python 3.10.x")
        return False
    
    # Verifica e instala pacotes
    for pacote, versao in versoes_necessarias['pacotes'].items():
        if pacote not in versoes_instaladas['pacotes']:
            instalar_pacote(pacote, versao)
        elif versao != 'latest' and versoes_instaladas['pacotes'][pacote] != versao:
            instalar_pacote(pacote, versao)

def instalar_pacote(pacote, versao):
    """Instala um pacote específico"""
    try:
        if versao == 'latest':
            comando = f"{sys.executable} -m pip install {pacote}"
        else:
            comando = f"{sys.executable} -m pip install {pacote}=={versao}"
        
        messagebox.showinfo("Instalação", f"Instalando {pacote} {versao}...")
        subprocess.check_call(comando.split())
        messagebox.showinfo("Sucesso", f"{pacote} {versao} instalado com sucesso!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Erro", f"Erro ao instalar {pacote}: {str(e)}")

if __name__ == "__main__":
    verificar_e_instalar()
