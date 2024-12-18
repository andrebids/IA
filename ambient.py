import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import argparse
import json
import torch
from PIL import Image, ImageTk
import datetime
import sys
import wandb
import threading
import random
import shutil
import numpy as np
import tkinter.scrolledtext as scrolledtext
import requests
from torchvision import transforms
import torchvision.transforms.functional as F
from glob import glob

# Adicionar a função build_transform
def build_transform(image_prep):
    """
    Constructs a transformation pipeline based on the specified image preparation method.
    """
    if image_prep == "resized_crop_512":
        T = transforms.Compose([
            transforms.Resize(512, interpolation=transforms.InterpolationMode.LANCZOS),
            transforms.CenterCrop(512),
        ])
    elif image_prep == "resize_286_randomcrop_256x256_hflip":
        T = transforms.Compose([
            transforms.Resize((286, 286), interpolation=Image.LANCZOS),
            transforms.RandomCrop((256, 256)),
            transforms.RandomHorizontalFlip(),
        ])
    elif image_prep in ["resize_256", "resize_256x256"]:
        T = transforms.Compose([
            transforms.Resize((256, 256), interpolation=Image.LANCZOS)
        ])
    elif image_prep in ["resize_512", "resize_512x512"]:
        T = transforms.Compose([
            transforms.Resize((512, 512), interpolation=Image.LANCZOS)
        ])
    elif image_prep == "no_resize":
        T = transforms.Lambda(lambda x: x)
    return T


# Definir caminhos
pasta_projeto = "C:\\Users\\AndreGarcia\\Desktop\\NtoD\\img2img-turbo"
pasta_dados = os.path.join(pasta_projeto, "data", "diaparanoite")
pasta_checkpoints = os.path.join(pasta_projeto, "checkpoints")
pasta_saida = os.path.join(pasta_projeto, "outputs")
arquivo_config = os.path.join(pasta_projeto, "config.json")

# Subpastas para dados
pasta_treino_dia = os.path.join(pasta_dados, "train_A")
pasta_treino_noite = os.path.join(pasta_dados, "train_B")
pasta_teste_dia = os.path.join(pasta_dados, "test_A")
pasta_teste_noite = os.path.join(pasta_dados, "test_B")

def criar_estrutura_pastas():
    """Cria a estrutura de pastas necessária para o projeto"""
    for pasta in [
        pasta_dados, pasta_checkpoints, pasta_saida,
        pasta_treino_dia, pasta_treino_noite,
        pasta_teste_dia, pasta_teste_noite
    ]:
        os.makedirs(pasta, exist_ok=True)
    
    # Criar arquivo de configuração se não existir
    if not os.path.exists(arquivo_config):
        config_inicial = {}  # Dicionário vazio inicial
        salvar_configuracoes(config_inicial)
    
    # Criar arquivos de prompt se não existirem
    prompt_dia_path = os.path.join(pasta_dados, "fixed_prompt_a.txt")
    prompt_noite_path = os.path.join(pasta_dados, "fixed_prompt_b.txt")
    
    if not os.path.exists(prompt_dia_path):
        with open(prompt_dia_path, "w") as f:
            f.write("uma fotografia durante o dia com luz natural")
    
    if not os.path.exists(prompt_noite_path):
        with open(prompt_noite_path, "w") as f:
            f.write("uma fotografia durante a noite com iluminação artificial")

def verificar_diretorios():
    """Verifica se todos os diretórios necessários existem e estão corretos"""
    criar_estrutura_pastas()
    
    # Verificar se existem imagens nas pastas
    imagens_treino_dia = len([f for f in os.listdir(pasta_treino_dia) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    imagens_treino_noite = len([f for f in os.listdir(pasta_treino_noite) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    imagens_teste_dia = len([f for f in os.listdir(pasta_teste_dia) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    imagens_teste_noite = len([f for f in os.listdir(pasta_teste_noite) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    
    mensagem = f"""
    Estrutura de pastas:
    
    Treino:
    - Dia (train_A): {imagens_treino_dia} imagens
    - Noite (train_B): {imagens_treino_noite} imagens
    
    Teste:
    - Dia (test_A): {imagens_teste_dia} imagens
    - Noite (test_B): {imagens_teste_noite} imagens
    
    Pastas do projeto:
    - Dados: {pasta_dados}
    - Checkpoints: {pasta_checkpoints}
    - Saída: {pasta_saida}
    """
    
    messagebox.showinfo("Verificação de Diretórios", mensagem)

# Variáveis globais
historico_treinamento = []
caminho_historico = os.path.join(pasta_projeto, "historico.json")

# Criar a janela principal
janela = tk.Tk()
janela.title("Conversor Dia para Noite")
janela.geometry("800x600")
janela.configure(bg="#f0f0f0")

# Criar notebook
notebook = ttk.Notebook(janela)
notebook.pack(fill=tk.BOTH, expand=True)

# Definir variáveis
wandb_api_key = tk.StringVar()
wandb_project_name = tk.StringVar()
passos_treinamento = tk.StringVar(value="1000")
taxa_aprendizagem = tk.StringVar(value="0.0001")
tamanho_lote = tk.StringVar(value="1")
passos_checkpoint = tk.StringVar(value="500") 

# Adicionar variável global
continuar_treino = tk.BooleanVar(value=True)

# Funções de configuração
def carregar_configuracoes():
    """Carrega as configurações do arquivo JSON"""
    try:
        if os.path.exists(arquivo_config):
            with open(arquivo_config, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Erro ao carregar configurações: {str(e)}")
        return {}

def salvar_configuracoes(config):
    """Salva as configurações em um arquivo JSON"""
    try:
        with open(arquivo_config, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Erro ao salvar configuraçes: {str(e)}")

def salvar_configuracoes_atuais():
    """Salva todas as configurações atuais"""
    config = {
        'wandb_api_key': wandb_api_key.get(),
        'wandb_project_name': wandb_project_name.get(),
        'passos_treinamento': passos_treinamento.get(),
        'taxa_aprendizagem': taxa_aprendizagem.get(),
        'tamanho_lote': tamanho_lote.get()
    }
    salvar_configuracoes(config)
    messagebox.showinfo("Sucesso", "Configurações salvas com sucesso!")

def carregar_configuracoes_iniciais():
    """Carrega as configurações iniciais do arquivo"""
    try:
        config = carregar_configuracoes()
        
        # Carregar configurações do W&B
        if 'wandb_api_key' in config:
            wandb_api_key.set(config['wandb_api_key'])
        if 'wandb_project_name' in config:
            wandb_project_name.set(config['wandb_project_name'])
        
        # Carregar outras configurações
        if 'passos_checkpoint' in config:
            passos_checkpoint.set(config['passos_checkpoint'])
        if 'passos_treinamento' in config:
            passos_treinamento.set(config['passos_treinamento'])
        if 'taxa_aprendizagem' in config:
            taxa_aprendizagem.set(config['taxa_aprendizagem'])
        if 'tamanho_lote' in config:
            tamanho_lote.set(config['tamanho_lote'])
            
        print("Configurações carregadas:", config)  # Debug para verificar o que está sendo carregado
    except Exception as e:
        print(f"Erro ao carregar configurações iniciais: {str(e)}")
        messagebox.showerror("Erro", f"Erro ao carregar configurações: {str(e)}")

def atualizar_configuracao(chave, valor):
    """Atualiza uma configuração específica"""
    config = carregar_configuracoes()
    config[chave] = valor
    salvar_configuracoes(config)

def callback(*args):
    """Callback para quando os valores das variáveis são alterados"""
    config = {
        'wandb_api_key': wandb_api_key.get(),
        'wandb_project_name': wandb_project_name.get(),
        'passos_treinamento': passos_treinamento.get(),
        'taxa_aprendizagem': taxa_aprendizagem.get(),
        'tamanho_lote': tamanho_lote.get(),
        'passos_checkpoint': passos_checkpoint.get()  # Adicionar nova configuração

    }
    salvar_configuracoes(config)

def adicionar_observadores():
    """Adiciona observadores para salvar configurações automaticamente"""
    wandb_api_key.trace_add("write", callback)
    wandb_project_name.trace_add("write", callback)
    passos_treinamento.trace_add("write", callback)
    taxa_aprendizagem.trace_add("write", callback)
    tamanho_lote.trace_add("write", callback)
    passos_checkpoint.trace_add("write", callback)

# Funções de histórico
def carregar_historico():
    global historico_treinamento
    try:
        if os.path.exists(caminho_historico):
            with open(caminho_historico, 'r') as f:
                historico_treinamento = json.load(f)
    except Exception as e:
        print(f"Erro ao carregar histórico: {e}")
        historico_treinamento = []

def salvar_historico():
    try:
        with open(caminho_historico, 'w') as f:
            json.dump(historico_treinamento, f, indent=4)
    except Exception as e:
        print(f"Erro ao salvar histórico: {e}")

def adicionar_ao_historico(info_treinamento):
    historico_treinamento.append(info_treinamento)
    salvar_historico()

# Definir todas as funções primeiro
def atualizar_diffusers():
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "diffusers"])
        messagebox.showinfo("Sucesso", "A biblioteca diffusers foi atualizada.")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Erro", f"Falha ao atualizar diffusers: {e}")

def atualizar_dependencias():
    dependencias = ["diffusers", "transformers", "accelerate", "peft"]
    for dep in dependencias:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", dep])
            print(f"Atualizado: {dep}")
        except subprocess.CalledProcessError as e:
            print(f"Erro ao atualizar {dep}: {e}")
    messagebox.showinfo("Atualização Concluída", "As dependências foram atualizadas.")
    
def reinstalar_huggingface():
    """Reinstala a versão específica do huggingface-hub"""
    try:
        # Primeiro desinstala a versão atual
        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "huggingface-hub", "-y"])
        messagebox.showinfo("Progresso", "Huggingface-hub desinstalado. Instalando versão 0.25.2...")
        
        # Instala a versão específica
        subprocess.check_call([sys.executable, "-m", "pip", "install", "huggingface-hub==0.25.2"])
        messagebox.showinfo("Sucesso", "Huggingface-hub 0.25.2 instalado com sucesso!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Erro", f"Falha ao reinstalar huggingface-hub: {e}")

def instalar_triton():
    triton_url = "https://huggingface.co/madbuda/triton-windows-builds/resolve/main/triton-3.0.0-cp310-cp310-win_amd64.whl"
    try:
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
        os.makedirs(temp_dir, exist_ok=True)
        triton_file = os.path.join(temp_dir, "triton-3.0.0-cp310-cp310-win_amd64.whl")
        print("Baixando Triton...")
        response = requests.get(triton_url)
        with open(triton_file, 'wb') as f:
            f.write(response.content)
        print("Instalando Triton...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", triton_file])
        os.remove(triton_file)
        messagebox.showinfo("Sucesso", "Triton instalado com sucesso.")
    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao instalar Triton: {e}")
    finally:
        try:
            os.rmdir(temp_dir)
        except:
            pass

def executar_treinamento():
    try:
        # Verificar se existe checkpoint anterior
        checkpoints_existentes = [f for f in os.listdir(pasta_checkpoints) if f.endswith('.pkl')]
        ultimo_checkpoint = None
        
        if checkpoints_existentes:
            # Ordenar por data de modificação
            checkpoints_existentes.sort(key=lambda x: os.path.getmtime(os.path.join(pasta_checkpoints, x)))
            ultimo_checkpoint = os.path.join(pasta_checkpoints, checkpoints_existentes[-1])
        
        # Configurar comando base
        comando = [
            sys.executable,
            os.path.join(pasta_projeto, "src", "train_cyclegan_turbo.py"),
            "--dataset_folder", pasta_dados,
            "--output_dir", pasta_checkpoints,
        ]
        
        # Adicionar checkpoint se existir
        if continuar_treino.get() and ultimo_checkpoint:
            comando.extend([
                "--resume_from_checkpoint", ultimo_checkpoint,
                "--continue_training"
            ])
        
        # Definir o método de transformação que será usado
        transform_method = "resize_256x256"
        T = build_transform(transform_method)
        
        # Carregar configurações salvas
        config = carregar_configuracoes()
        
        comando.extend([
            "--train_img_prep", transform_method,
            "--val_img_prep", transform_method,
            "--tracker_project_name", config.get('wandb_project_name', 'diaparanoite'),
            "--checkpointing_steps", passos_checkpoint.get(),
            # Argumentos obrigatórios
            "--dataset_folder", pasta_dados,
            "--train_img_prep", transform_method,  # Usar a mesma transformação definida acima
            "--val_img_prep", transform_method,    # Usar a mesma transformação para validação
            "--output_dir", pasta_checkpoints,  # Alterado de pasta_saida para pasta_checkpoints
            "--tracker_project_name", config.get('wandb_project_name', 'diaparanoite'),
            
            # Argumentos do modelo
            "--pretrained_model_name_or_path", "stabilityai/sd-turbo",
            "--lora_rank_unet", "128",  # Valor padrão do training_utils.py
            "--lora_rank_vae", "4",     # Valor padrão do training_utils.py
            
            # Argumentos de treinamento
            "--max_train_steps", passos_treinamento.get(),
            "--learning_rate", taxa_aprendizagem.get(),
            "--train_batch_size", tamanho_lote.get(),
            
            # Argumentos do GAN
            "--lambda_gan", "0.5",
            "--lambda_cycle", "1",
            "--lambda_idt", "1",
            "--lambda_cycle_lpips", "10.0",
            "--lambda_idt_lpips", "1.0",
            
            # Otimização e memória
            "--gradient_accumulation_steps", "1",
            "--enable_xformers_memory_efficient_attention",
            "--gradient_checkpointing",
            "--allow_tf32",  
            "--mixed_precision", "fp16",    # Adicionar mixed precision
            "--allow_tf32",
            
            # Validação e logging
            "--validation_steps", "500",
            "--report_to", "wandb"
        ])

        # Configurar variável de ambiente NCCL_P2P_DISABLE
        os.environ["NCCL_P2P_DISABLE"] = "1"
        os.environ["WANDB_API_KEY"] = config.get('wandb_api_key', '')

        # Registrar início do treino
        info_treinamento = {
            'data_inicio': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'passos': passos_treinamento.get(),
            'taxa_aprendizagem': taxa_aprendizagem.get(),
            'tamanho_lote': tamanho_lote.get(),
            'projeto_wandb': config.get('wandb_project_name', 'diaparanoite')
        }
        
        # Criar janela de progresso
        janela_progresso = tk.Toplevel(janela)
        janela_progresso.title("Progresso do Treino")
        janela_progresso.geometry("600x400")
        
        texto_progresso = scrolledtext.ScrolledText(janela_progresso, wrap=tk.WORD, width=70, height=20)
        texto_progresso.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        processo = subprocess.Popen(
            comando, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True, 
            bufsize=1, 
            universal_newlines=True
        )
        
        def atualizar_progresso():
            output = processo.stdout.readline()
            if output:
                texto_progresso.insert(tk.END, output)
                texto_progresso.see(tk.END)
                janela.after(10, atualizar_progresso)
            elif processo.poll() is not None:
                rc = processo.poll()
                if rc == 0:
                    info_treinamento['status'] = 'concluído'
                    messagebox.showinfo("Sucesso", "Treino concluído!")
                else:
                    info_treinamento['status'] = 'falhou'
                    messagebox.showerror("Erro", f"Falha no treino: {rc}")
                info_treinamento['data_fim'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                adicionar_ao_historico(info_treinamento)
                janela_progresso.destroy()
        
        janela.after(10, atualizar_progresso)
        
    except Exception as e:
        # Atualizar status para 'erro' em caso de exceção
        info_treinamento['status'] = 'erro'
        info_treinamento['erro'] = str(e)
        messagebox.showerror("Erro", f"Erro ao executar treinamento: {str(e)}")
    finally:
        # Adicionar ao histórico independentemente do resultado
        adicionar_ao_historico(info_treinamento)

def testar_conexao_wandb():
    api_key = wandb_api_key.get()
    if not api_key:
        messagebox.showerror("Erro", "Insira a API Key do W&B")
        return
    try:
        wandb.login(key=api_key)
        messagebox.showinfo("Sucesso", "Conexão W&B OK!")
    except Exception as e:
        messagebox.showerror("Erro", f"Falha W&B: {e}")

def mostrar_arquivos_gerados():
    try:
        os.startfile(pasta_checkpoints)
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao abrir pasta: {e}")

def gerar_conjuntos_teste():
    try:
        # Verifica se existem as pastas necessárias
        for pasta in [pasta_treino_dia, pasta_treino_noite, pasta_teste_dia, pasta_teste_noite]:
            os.makedirs(pasta, exist_ok=True)
        
        # Obter imagens das pastas de treino atuais
        imagens_dia = [f for f in os.listdir(pasta_treino_dia) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        imagens_noite = [f for f in os.listdir(pasta_treino_noite) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        if not imagens_dia or not imagens_noite:
            messagebox.showwarning("Aviso", "Sem imagens suficientes nas pastas de treino.")
            return
        
        # Calcular quantidade de imagens para teste (20%)
        num_teste_dia = max(1, int(len(imagens_dia) * 0.2))
        num_teste_noite = max(1, int(len(imagens_noite) * 0.2))
        
        # Selecionar aleatoriamente imagens para teste
        imagens_teste_dia = random.sample(imagens_dia, num_teste_dia)
        imagens_teste_noite = random.sample(imagens_noite, num_teste_noite)
        
        # Mover imagens dia
        for imagem in imagens_teste_dia:
            origem = os.path.join(pasta_treino_dia, imagem)
            destino = os.path.join(pasta_teste_dia, imagem)
            shutil.move(origem, destino)
        
        # Mover imagens noite
        for imagem in imagens_teste_noite:
            origem = os.path.join(pasta_treino_noite, imagem)
            destino = os.path.join(pasta_teste_noite, imagem)
            shutil.move(origem, destino)
        
        # Mostrar resumo
        mensagem = f"""Divisão concluída:
        Dia:
        - Treino: {len(imagens_dia) - num_teste_dia}
        - Teste: {num_teste_dia}
        
        Noite:
        - Treino: {len(imagens_noite) - num_teste_noite}
        - Teste: {num_teste_noite}"""
        
        messagebox.showinfo("Sucesso", mensagem)
        
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao dividir imagens: {str(e)}")

def mostrar_historico():
    janela_historico = tk.Toplevel(janela)
    janela_historico.title("Histórico de Treinamentos")
    janela_historico.geometry("800x400")
    
    texto_historico = scrolledtext.ScrolledText(janela_historico, wrap=tk.WORD, width=90, height=20)
    texto_historico.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    
    for i, treino in enumerate(historico_treinamento, 1):
        texto = f"\n=== Treinamento {i} ===\n"
        texto += f"Data Início: {treino.get('data_inicio', 'N/A')}\n"
        texto += f"Data Fim: {treino.get('data_fim', 'N/A')}\n"
        texto += f"Status: {treino.get('status', 'N/A')}\n"
        texto += f"Passos: {treino.get('passos', 'N/A')}\n"
        texto += f"Taxa de Aprendizagem: {treino.get('taxa_aprendizagem', 'N/A')}\n"
        texto += f"Tamanho do Lote: {treino.get('tamanho_lote', 'N/A')}\n"
        texto += f"Projeto W&B: {treino.get('projeto_wandb', 'N/A')}\n"
        if 'erro' in treino:
            texto += f"Erro: {treino['erro']}\n"
        texto += "="*30 + "\n"
        texto_historico.insert(tk.END, texto)
    
    texto_historico.configure(state='disabled')

def mostrar_info_checkpoint():
    checkpoints = [f for f in os.listdir(pasta_checkpoints) if f.endswith('.pkl')]
    if not checkpoints:
        messagebox.showinfo("Info", "Nenhum checkpoint encontrado")
        return
        
    ultimo_checkpoint = max(
        checkpoints,
        key=lambda x: os.path.getmtime(os.path.join(pasta_checkpoints, x))
    )
    
    data_modificacao = datetime.datetime.fromtimestamp(
        os.path.getmtime(os.path.join(pasta_checkpoints, ultimo_checkpoint))
    ).strftime("%d/%m/%Y %H:%M:%S")
    
    mensagem = f"""
    Último checkpoint: {ultimo_checkpoint}
    Data: {data_modificacao}
    """
    messagebox.showinfo("Info do Checkpoint", mensagem)

# Aba de Conversão
aba_conversao = ttk.Frame(notebook)
notebook.add(aba_conversao, text="Conversão")

caminho_imagem = tk.StringVar()
caminho_resultado = tk.StringVar()
modelo_selecionado = tk.StringVar()

frame_principal = ttk.Frame(aba_conversao, padding="10")
frame_principal.pack(fill=tk.BOTH, expand=True)

frame_imagens = ttk.Frame(frame_principal)
frame_imagens.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

label_imagem = ttk.Label(frame_imagens)
label_imagem.pack(pady=10)

label_resultado = ttk.Label(frame_imagens)
label_resultado.pack(pady=10)

frame_botoes = ttk.Frame(frame_principal)
frame_botoes.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))

# Função para atualizar a lista de modelos disponíveis
def atualizar_lista_modelos():
    modelos = ["Modelo Padrão"]  # Sempre inclui o modelo padrão
    
    if os.path.exists(pasta_checkpoints):
        modelos.extend([f for f in os.listdir(pasta_checkpoints) if f.endswith('.pkl')])
    
    combobox_modelos['values'] = modelos
    if modelos:
        combobox_modelos.set(modelos[-1])  # Seleciona o último modelo da lista
    
    # Se não houver modelos treinados, desabilita o Combobox
    if len(modelos) == 1:
        combobox_modelos.set("Modelo Padrão")
        combobox_modelos.config(state="disabled")
    else:
        combobox_modelos.config(state="readonly")

# Campo para seleção do modelo
ttk.Label(frame_botoes, text="Selecione o Modelo:").pack(pady=(0, 5))
combobox_modelos = ttk.Combobox(frame_botoes, textvariable=modelo_selecionado, state="readonly")
combobox_modelos.pack(pady=(0, 10), fill=tk.X)
atualizar_lista_modelos()  # Preenche a lista de modelos inicialmente

historico = []

def carregar_historico():
    global historico
    arquivo_historico = os.path.join(pasta_projeto, "historico.json")
    if os.path.exists(arquivo_historico):
        with open(arquivo_historico, 'r') as f:
            historico = json.load(f)
    atualizar_historico()

def salvar_historico():
    arquivo_historico = os.path.join(pasta_projeto, "historico.json")
    with open(arquivo_historico, 'w') as f:
        json.dump(historico, f)

def selecionar_imagem():
    arquivo = filedialog.askopenfilename(filetypes=[("Imagens", "*.png *.jpg *.jpeg")])
    if arquivo:
        caminho_imagem.set(arquivo)
        exibir_imagem(arquivo, label_imagem)

def exibir_imagem(caminho, label):
    imagem = Image.open(caminho)
    imagem = imagem.resize((300, 200), Image.LANCZOS)
    foto = ImageTk.PhotoImage(imagem)
    label.config(image=foto)
    label.image = foto

def converter_imagem():
    entrada = caminho_imagem.get()
    if not entrada:
        messagebox.showerror("Erro", "Por favor, selecione uma imagem primeiro.")
        return

    modelo = modelo_selecionado.get()
    comando = [
        "python",
        os.path.join(pasta_projeto, "src", "inference_unpaired.py"),
        "--input_image", entrada,
        "--output_dir", pasta_saida,
        "--image_prep", "resize_512x512",
        "--use_fp16"
    ]

    if modelo == "Modelo Padrão":
        comando.extend(["--model_name", "stabilityai/sd-turbo"])
    else:
        comando.extend([
            "--model_path", os.path.join(pasta_checkpoints, modelo),
            "--prompt", "noite",
            "--direction", "a2b"
        ])

    try:
        subprocess.run(comando, check=True, cwd=pasta_projeto)
        messagebox.showinfo("Sucesso", "Imagem convertida com sucesso!")
        
        nome_arquivo = os.path.basename(entrada)
        caminho_saida = os.path.join(pasta_saida, nome_arquivo)
        caminho_resultado.set(caminho_saida)
        exibir_imagem(caminho_saida, label_resultado)
        
        data_hora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        historico.append(f"{data_hora} - {nome_arquivo} (Modelo: {modelo})")
        atualizar_historico()
        salvar_historico()
        botao_abrir_resultado.config(state=tk.NORMAL)
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Erro", f"Ocorreu um erro ao converter a imagem: {e}")
def reinstalar_diffusers():
    """Reinstala a versão específica do diffusers"""
    try:
        # Primeiro desinstala a versão atual
        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "diffusers", "-y"])
        messagebox.showinfo("Progresso", "Diffusers desinstalado. Instalando versão 0.25.1...")
        
        # Instala a versão específica
        subprocess.check_call([sys.executable, "-m", "pip", "install", "diffusers==0.25.1"])
        messagebox.showinfo("Sucesso", "Diffusers 0.25.1 instalado com sucesso!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Erro", f"Falha ao reinstalar diffusers: {e}")
def atualizar_historico():
    lista_historico.delete(0, tk.END)
    for item in historico[-10:]:  # Mostra apenas os últimos 10 itens
        lista_historico.insert(tk.END, item)

def abrir_resultado():
    caminho = caminho_resultado.get()
    if caminho:
        os.startfile(caminho)
    else:
        messagebox.showerror("Erro", "Nenhuma imagem convertida disponível.")

def abrir_resultado_historico(event):
    selecao = lista_historico.curselection()
    if selecao:
        indice = selecao[0]
        item = lista_historico.get(indice)
        # Extrair o nome do arquivo do item do histórico
        nome_arquivo = item.split(" - ")[1].split(" (Modelo:")[0]
        caminho_completo = os.path.join(pasta_saida, nome_arquivo)
        if os.path.exists(caminho_completo):
            os.startfile(caminho_completo)
        else:
            messagebox.showerror("Erro", f"O arquivo {nome_arquivo} não foi encontrado.")

estilo = ttk.Style()
estilo.configure("TButton", padding=10, font=("Arial", 12))

botao_selecionar = ttk.Button(frame_botoes, text="Selecionar Imagem", command=selecionar_imagem, style="TButton")
botao_selecionar.pack(pady=10, fill=tk.X)

botao_converter = ttk.Button(frame_botoes, text="Converter para Noite", command=converter_imagem, style="TButton")
botao_converter.pack(pady=10, fill=tk.X)

botao_abrir_resultado = ttk.Button(frame_botoes, text="Abrir Resultado", command=abrir_resultado, style="TButton", state=tk.DISABLED)
botao_abrir_resultado.pack(pady=10, fill=tk.X)

# Botão para atualizar a lista de modelos
botao_atualizar_modelos = ttk.Button(frame_botoes, text="Atualizar Lista de Modelos", command=atualizar_lista_modelos)
botao_atualizar_modelos.pack(pady=10, fill=tk.X)

frame_historico = ttk.Frame(frame_principal)
frame_historico.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

label_historico = ttk.Label(frame_historico, text="Histórico de Conversões", font=("Arial", 12, "bold"))
label_historico.pack(pady=(0, 5))

lista_historico = tk.Listbox(frame_historico, width=50, height=10, font=("Arial", 10))
lista_historico.pack(fill=tk.BOTH, expand=True)
lista_historico.bind('<Double-1>', abrir_resultado_historico)

# Adicionar uma label com instruções
label_instrucoes = ttk.Label(frame_historico, text="Clique duplo para abrir a imagem", font=("Arial", 9, "italic"))
label_instrucoes.pack(pady=(5, 0))

# Aba de Treinamento
aba_treinamento = ttk.Frame(notebook)
notebook.add(aba_treinamento, text="Treinamento")

# Frame principal do treinamento com duas colunas
frame_treinamento = ttk.Frame(aba_treinamento, padding="10")
frame_treinamento.pack(fill=tk.BOTH, expand=True)

# Frame para configurações (coluna esquerda)
frame_config = ttk.LabelFrame(frame_treinamento, text="Configurações", padding="10")
frame_config.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")

# Frame para ações (coluna direita)
frame_acoes = ttk.LabelFrame(frame_treinamento, text="Ações", padding="10")
frame_acoes.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")

# Configurar o grid para expandir corretamente
frame_treinamento.columnconfigure(0, weight=1)
frame_treinamento.columnconfigure(1, weight=1)

# Adicionar configurações no frame_config
ttk.Label(frame_config, text="Chave API do W&B:").grid(row=0, column=0, sticky="w", pady=5)
ttk.Entry(frame_config, textvariable=wandb_api_key, width=40).grid(row=0, column=1, sticky="ew", pady=5)

ttk.Label(frame_config, text="Nome do Projeto W&B:").grid(row=1, column=0, sticky="w", pady=5)
ttk.Entry(frame_config, textvariable=wandb_project_name, width=40).grid(row=1, column=1, sticky="ew", pady=5)

# Frame para parâmetros de treino
frame_params = ttk.LabelFrame(frame_config, text="Parâmetros de Treino", padding="5")
frame_params.grid(row=2, column=0, columnspan=2, sticky="ew", pady=10)

ttk.Label(frame_params, text="Número de passos:").grid(row=0, column=0, sticky="w", pady=5)
ttk.Entry(frame_params, textvariable=passos_treinamento, width=10).grid(row=0, column=1, sticky="w", pady=5)

ttk.Label(frame_params, text="Taxa de aprendizagem:").grid(row=1, column=0, sticky="w", pady=5)
ttk.Entry(frame_params, textvariable=taxa_aprendizagem, width=10).grid(row=1, column=1, sticky="w", pady=5)

ttk.Label(frame_params, text="Tamanho do lote:").grid(row=2, column=0, sticky="w", pady=5)
ttk.Entry(frame_params, textvariable=tamanho_lote, width=10).grid(row=2, column=1, sticky="w", pady=5)

# Na seção de configurações do frame_params
ttk.Label(frame_params, text="Passos para checkpoint:").grid(row=3, column=0, sticky="w", pady=5)
ttk.Entry(frame_params, textvariable=passos_checkpoint, width=10).grid(row=3, column=1, sticky="w", pady=5)

# No frame de parâmetros de treino
ttk.Checkbutton(
    frame_params, 
    text="Continuar último treino", 
    variable=continuar_treino
).grid(row=4, column=0, columnspan=2, sticky="w", pady=5)

def configurar_ambiente():
    """Configura o ambiente com todas as dependências necessárias"""
    try:
        # Lista de pacotes com versões específicas
        pacotes = [
            "torch==2.0.1",
            "torchvision==0.15.2",
            "diffusers==0.25.1",
            "huggingface-hub==0.25.2",
            "transformers==4.30.2",
            "accelerate==0.20.3",
            "wandb",
            "pillow",
            "tqdm",
            "numpy"
        ]
        
        for pacote in pacotes:
            messagebox.showinfo("Progresso", f"Instalando {pacote}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pacote])
        
        messagebox.showinfo("Sucesso", "Ambiente configurado com sucesso!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Erro", f"Falha ao configurar ambiente: {e}")

# Botões principais no frame_acoes
botoes_principais = [
    ("Iniciar Treino", executar_treinamento),
    ("Testar Ligação W&B", testar_conexao_wandb),
    ("Mostrar Ficheiros Gerados", mostrar_arquivos_gerados),
    ("Verificar Pastas", verificar_diretorios),
    ("Dividir Imagens (Treino/Teste)", gerar_conjuntos_teste),
    ("Ver Histórico", mostrar_historico),
    ("Reinstalar Diffusers 0.25.1", reinstalar_diffusers),
    ("Reinstalar Huggingface 0.25.2", reinstalar_huggingface),
    ("Configurar Novo Ambiente", configurar_ambiente)
]

for i, (texto, comando) in enumerate(botoes_principais):
    ttk.Button(frame_acoes, text=texto, command=comando).grid(row=i, column=0, pady=5, sticky="ew")

# Configurar expansão dos frames
for frame in [frame_config, frame_acoes]:
    frame.columnconfigure(1, weight=1)

# Carregar dados no início
carregar_configuracoes_iniciais()  # Alterado de carregar_configuracoes() para carregar_configuracoes_iniciais()
carregar_historico()
adicionar_observadores()

# Iniciar o loop principal
janela.mainloop()

def salvar_wandb_key():
    """Salva a chave da API do W&B nas configurações"""
    try:
        chave = wandb_api_key.get()
        projeto = wandb_project_name.get()
        
        if not chave or not projeto:
            messagebox.showerror("Erro", "Por favor, preencha a chave da API e o nome do projeto")
            return
        
        config = carregar_configuracoes()
        config['wandb_api_key'] = chave
        config['wandb_project_name'] = projeto
        salvar_configuracoes(config)
        
        print("Configurações salvas:", config)  # Debug para verificar o que está sendo salvo
        messagebox.showinfo("Sucesso", "Configurações do W&B salvas com sucesso!")
    except Exception as e:
        print(f"Erro ao salvar chave W&B: {str(e)}")
        messagebox.showerror("Erro", f"Erro ao salvar configurações: {str(e)}")








