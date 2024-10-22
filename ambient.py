import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import json
from PIL import Image, ImageTk
import datetime
import sys
import wandb
import threading
import random
import shutil
import numpy as np

# Defina o caminho base do projeto
pasta_projeto = "C:\\Users\\AndreGarcia\\Desktop\\NtoD\\img2img-turbo"

# Defina o caminho para a pasta de checkpoints
pasta_checkpoints = os.path.join(pasta_projeto, "checkpoints")

pasta_saida = os.path.join(pasta_projeto, "outputs")
arquivo_config = os.path.join(pasta_projeto, "config.json")

janela = tk.Tk()
janela.title("Conversor Dia para Noite")
janela.geometry("800x600")
janela.configure(bg="#f0f0f0")

notebook = ttk.Notebook(janela)
notebook.pack(fill=tk.BOTH, expand=True)

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
        combobox_modelos.set(modelos[0])
    
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
        botao_abrir_resultado.config(state=tk.NORMAL)
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Erro", f"Ocorreu um erro ao converter a imagem: {e}")

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

# Aba de Treinamento
aba_treinamento = ttk.Frame(notebook)
notebook.add(aba_treinamento, text="Treinamento")

frame_treinamento = ttk.Frame(aba_treinamento, padding="10")
frame_treinamento.pack(fill=tk.BOTH, expand=True)

# Variáveis para as pastas de treinamento e API key
pasta_trainA = tk.StringVar()
pasta_trainB = tk.StringVar()
pasta_testA = tk.StringVar()
pasta_testB = tk.StringVar()
wandb_api_key = tk.StringVar()
wandb_project_name = tk.StringVar()

def carregar_configuracoes():
    if os.path.exists(arquivo_config):
        with open(arquivo_config, 'r') as f:
            config = json.load(f)
            pasta_trainA.set(config.get('pasta_trainA', ''))
            pasta_trainB.set(config.get('pasta_trainB', ''))
            pasta_testA.set(config.get('pasta_testA', ''))
            pasta_testB.set(config.get('pasta_testB', ''))
            wandb_api_key.set(config.get('wandb_api_key', ''))
            wandb_project_name.set(config.get('wandb_project_name', ''))

def salvar_configuracoes():
    config = {
        'pasta_trainA': pasta_trainA.get(),
        'pasta_trainB': pasta_trainB.get(),
        'pasta_testA': pasta_testA.get(),
        'pasta_testB': pasta_testB.get(),
        'wandb_api_key': wandb_api_key.get(),
        'wandb_project_name': wandb_project_name.get()
    }
    with open(arquivo_config, 'w') as f:
        json.dump(config, f)

def selecionar_pasta(variavel):
    pasta = filedialog.askdirectory()
    if pasta:
        variavel.set(pasta)
        salvar_configuracoes()

# Campos para seleção de pastas com explicações
ttk.Label(frame_treinamento, text="Pasta trainA (Imagens de dia para treinamento):", wraplength=200).grid(row=0, column=0, sticky="w", pady=5)
ttk.Entry(frame_treinamento, textvariable=pasta_trainA, width=50).grid(row=0, column=1, pady=5)
ttk.Button(frame_treinamento, text="Selecionar", command=lambda: selecionar_pasta(pasta_trainA)).grid(row=0, column=2, pady=5)

ttk.Label(frame_treinamento, text="Pasta trainB (Imagens de noite para treinamento):", wraplength=200).grid(row=1, column=0, sticky="w", pady=5)
ttk.Entry(frame_treinamento, textvariable=pasta_trainB, width=50).grid(row=1, column=1, pady=5)
ttk.Button(frame_treinamento, text="Selecionar", command=lambda: selecionar_pasta(pasta_trainB)).grid(row=1, column=2, pady=5)

ttk.Label(frame_treinamento, text="Pasta testA (Imagens de dia para teste):", wraplength=200).grid(row=2, column=0, sticky="w", pady=5)
ttk.Entry(frame_treinamento, textvariable=pasta_testA, width=50).grid(row=2, column=1, pady=5)
ttk.Button(frame_treinamento, text="Selecionar", command=lambda: selecionar_pasta(pasta_testA)).grid(row=2, column=2, pady=5)

ttk.Label(frame_treinamento, text="Pasta testB (Imagens de noite para teste):", wraplength=200).grid(row=3, column=0, sticky="w", pady=5)
ttk.Entry(frame_treinamento, textvariable=pasta_testB, width=50).grid(row=3, column=1, pady=5)
ttk.Button(frame_treinamento, text="Selecionar", command=lambda: selecionar_pasta(pasta_testB)).grid(row=3, column=2, pady=5)

# Adicionar um botão de ajuda para explicar melhor a estrutura das pastas
def mostrar_ajuda_pastas():
    mensagem = """
    Estrutura das pastas para treinamento do CycleGAN:

    trainA: Coloque aqui as imagens de dia que você quer usar para treinar o modelo.
    Exemplo: Fotos de paisagens, cidades ou objetos durante o dia.

    trainB: Coloque aqui as imagens de noite correspondentes ao tipo de cenas em trainA.
    Exemplo: Fotos de paisagens, cidades ou objetos durante a noite.

    testA: Coloque aqui algumas imagens de dia (diferentes das de trainA) para testar o modelo.
    Estas imagens serão usadas para verificar o desempenho do modelo durante o treinamento.

    testB: Coloque aqui algumas imagens de noite (diferentes das de trainB) para testar o modelo.
    Estas imagens também serão usadas para verificar o desempenho do modelo.

    Observações:
    - As imagens em trainA e trainB não precisam ser pares exatos (mesma cena de dia e noite).
    - Use imagens de alta qualidade e variadas para melhor treinamento.
    - Recomenda-se ter pelo menos algumas centenas de imagens em cada pasta de treinamento.
    """
    messagebox.showinfo("Ajuda - Estrutura das Pastas", mensagem)

ttk.Button(frame_treinamento, text="Ajuda sobre as Pastas", command=mostrar_ajuda_pastas).grid(row=4, column=1, pady=10)

# Campo para API key do wandb
ttk.Label(frame_treinamento, text="Wandb API Key:").grid(row=5, column=0, sticky="w", pady=5)
ttk.Entry(frame_treinamento, textvariable=wandb_api_key, width=50, show="*").grid(row=5, column=1, pady=5)

# Campo para nome do projeto wandb
ttk.Label(frame_treinamento, text="Wandb Project Name:").grid(row=6, column=0, sticky="w", pady=5)
ttk.Entry(frame_treinamento, textvariable=wandb_project_name, width=50).grid(row=6, column=1, pady=5)

def verificar_diretorios():
    diretorios = [pasta_trainA.get(), pasta_trainB.get(), pasta_testA.get(), pasta_testB.get()]
    for diretorio in diretorios:
        if not os.path.exists(diretorio) or not os.listdir(diretorio):
            return False
    return True

def gerar_conjuntos_teste():
    if not pasta_trainA.get() or not pasta_trainB.get():
        messagebox.showerror("Erro", "Por favor, selecione as pastas trainA e trainB primeiro.")
        return

    porcentagem_teste = 0.2  # 20% das imagens serão usadas para teste

    for origem, destino in [(pasta_trainA.get(), pasta_testA.get()), (pasta_trainB.get(), pasta_testB.get())]:
        todas_imagens = [f for f in os.listdir(origem) if f.endswith(('.png', '.jpg', '.jpeg'))]
        num_teste = int(len(todas_imagens) * porcentagem_teste)
        imagens_teste = random.sample(todas_imagens, num_teste)

        os.makedirs(destino, exist_ok=True)
        for img in imagens_teste:
            shutil.move(os.path.join(origem, img), os.path.join(destino, img))

    messagebox.showinfo("Sucesso", "Conjuntos de teste gerados com sucesso!")

def verificar_estrutura_dataset():
    diretorios = [pasta_trainA.get(), pasta_trainB.get(), pasta_testA.get(), pasta_testB.get()]
    for diretorio in diretorios:
        if not os.path.exists(diretorio):
            return False
        if not any(f.endswith(('.png', '.jpg', '.jpeg')) for f in os.listdir(diretorio)):
            return False
    return True

def preparar_dataset():
    diretorios = [pasta_trainA.get(), pasta_trainB.get(), pasta_testA.get(), pasta_testB.get()]
    for diretorio in diretorios:
        os.makedirs(diretorio, exist_ok=True)
    
    # Se testA e testB estiverem vazios, mova algumas imagens de trainA e trainB
    if not os.listdir(pasta_testA.get()):
        mover_imagens_para_teste(pasta_trainA.get(), pasta_testA.get())
    if not os.listdir(pasta_testB.get()):
        mover_imagens_para_teste(pasta_trainB.get(), pasta_testB.get())

def mover_imagens_para_teste(origem, destino, quantidade=10):
    imagens = [f for f in os.listdir(origem) if f.endswith(('.png', '.jpg', '.jpeg'))]
    for imagem in imagens[:quantidade]:
        shutil.move(os.path.join(origem, imagem), os.path.join(destino, imagem))

def executar_treinamento():
    if not verificar_estrutura_dataset():
        resposta = messagebox.askyesno("Aviso", "A estrutura do dataset não está correta. Deseja prepará-la automaticamente?")
        if resposta:
            preparar_dataset()
        else:
            messagebox.showerror("Erro", "Por favor, prepare o dataset manualmente e tente novamente.")
            return

    # Configuração do ambiente
    os.environ["PYTHONPATH"] = "."
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["NCCL_P2P_DISABLE"] = "1"
    os.environ["WANDB_API_KEY"] = wandb_api_key.get()

    # Comando de treinamento
    comando = f"""
    python src/train_cyclegan_turbo.py \
        --pretrained_model_name_or_path="stabilityai/sd-turbo" \
        --output_dir="output/cyclegan_turbo/my_dataset" \
        --dataset_folder="{os.path.dirname(pasta_trainA.get())}" \
        --train_img_prep "resize_286_randomcrop_256x256_hflip" --val_img_prep "no_resize" \
        --learning_rate="1e-5" --max_train_steps=25000 \
        --train_batch_size=1 --gradient_accumulation_steps=1 \
        --report_to "wandb" --tracker_project_name="{wandb_project_name.get()}" \
        --enable_xformers_memory_efficient_attention --validation_steps 250 \
        --lambda_gan 0.5 --lambda_idt 1 --lambda_cycle 1 \
        --mixed_precision="fp16" --use_8bit_adam
    """
    
    # Execução do comando
    process = subprocess.Popen(comando, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
    # Monitoramento do processo
    for line in process.stdout:
        print(line.decode(), end='')
    
    process.wait()
    
    if process.returncode == 0:
        messagebox.showinfo("Sucesso", "Treinamento concluído com sucesso!")
    else:
        messagebox.showerror("Erro", f"Ocorreu um erro durante o treinamento. Código de saída: {process.returncode}")

def testar_conexao_wandb():
    if not wandb_api_key.get():
        messagebox.showerror("Erro", "Por favor, insira a API key do Weights & Biases.")
        return

    try:
        import wandb
    except ImportError:
        resposta = messagebox.askyesno("Módulo não encontrado", "O módulo wandb não está instalado. Deseja instalá-lo agora?")
        if resposta:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "wandb"])
                messagebox.showinfo("Sucesso", "O módulo wandb foi instalado com sucesso. Por favor, reinicie o aplicativo.")
                return
            except subprocess.CalledProcessError as e:
                messagebox.showerror("Erro", f"Falha ao instalar o módulo wandb: {e}")
                return
        else:
            return

    try:
        wandb.login(key=wandb_api_key.get())
        messagebox.showinfo("Sucesso", "Conexão com wandb.ai estabelecida com sucesso!")
        salvar_configuracoes()
    except Exception as e:
        messagebox.showerror("Erro", f"Falha na conexão com wandb.ai: {e}")

def mostrar_arquivos_gerados():
    diretorio_saida = os.path.join(pasta_projeto, "output", "cyclegan_turbo", "my_dataset")
    if not os.path.exists(diretorio_saida):
        messagebox.showinfo("Informação", "O diretório de saída ainda não foi criado. Execute o treinamento primeiro.")
        return

    mensagem = "Arquivos e diretórios gerados:\n\n"
    for root, dirs, files in os.walk(diretorio_saida):
        nivel = root.replace(diretorio_saida, '').count(os.sep)
        indent = ' ' * 4 * nivel
        mensagem += f"{indent}{os.path.basename(root)}/\n"
        sub_indent = ' ' * 4 * (nivel + 1)
        for f in files:
            mensagem += f"{sub_indent}{f}\n"

    messagebox.showinfo("Arquivos Gerados", mensagem)

# Botões reorganizados
ttk.Button(frame_treinamento, text="Iniciar Treinamento", command=executar_treinamento).grid(row=7, column=1, pady=10)
ttk.Button(frame_treinamento, text="Testar Conexão wandb.ai", command=testar_conexao_wandb).grid(row=8, column=1, pady=10)
ttk.Button(frame_treinamento, text="Mostrar Arquivos Gerados", command=mostrar_arquivos_gerados).grid(row=9, column=1, pady=10)
ttk.Button(frame_treinamento, text="Verificar Diretórios", command=verificar_diretorios).grid(row=10, column=1, pady=10)
ttk.Button(frame_treinamento, text="Gerar Conjuntos de Teste", command=gerar_conjuntos_teste).grid(row=11, column=1, pady=10)

# Carregar configurações salvas
carregar_configuracoes()

janela.mainloop()
