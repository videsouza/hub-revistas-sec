import os
from sickle import Sickle
from supabase import create_client, Client

# Lendo as chaves seguras configuradas no GitHub
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    print("Erro: Chaves de configuração não encontradas no ambiente.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Configuração da revista alvo (Mude aqui se quiser testar outra revista)
nome_revista = "Ciência da Informação (IBICT)"
url_oai = "https://revista.ibict.br/ciinf/oai"
area_revista = "Ciência da Informação"

print(f"Iniciando conexão OAI-PMH com: {nome_revista}")
sickle = Sickle(url_oai)

# 1. Verifica se a revista já existe no banco, se não, cria automaticamente
res_revista = supabase.table('revistas').select('id').eq('nome', nome_revista).execute()
if not res_revista.data:
    print(f"Cadastrando a revista '{nome_revista}' no banco...")
    res_nova = supabase.table('revistas').insert({
        "nome": nome_revista,
        "issn": "1518-8353",
        "area": area_revista
    }).execute()
    revista_id = res_nova.data[0]['id']
else:
    revista_id = res_revista.data[0]['id']

# Dicionário em memória para evitar requisições repetidas de edições
edicoes_cadastradas = {}

# 2. Inicia a colheita (Vamos limitar a 50 registros para o primeiro teste online rodar rápido)
print("Baixando registros do protocolo...")
records = sickle.ListRecords(metadataPrefix='oai_dc', ignore_deleted=True)

contador = 0
for record in records:
    if contador >= 50: # Trava de segurança para o primeiro teste
        break
        
    metadata = record.metadata
    
    titulo = metadata.get('title', [''])[0]
    autores = ", ".join(metadata.get('creator', []))
    resumo = metadata.get('description', [''])[0]
    data_pub = metadata.get('date', [''])[0]
    
    identificadores = metadata.get('identifier', [])
    link_pdf = next((link for link in identificadores if 'http' in link), None)
    source = metadata.get('source', [''])[0]
    
    if not titulo or not source:
        continue

    ano = int(data_pub[:4]) if data_pub and data_pub[:4].isdigit() else 0
    chave_edicao = source 
    
    # 3. Gerenciamento da Edição
    if chave_edicao not in edicoes_cadastradas:
        # Verifica se já está no banco
        res_ed = supabase.table('edicoes').select('id').eq('volume', chave_edicao).eq('revista_id', revista_id).execute()
        if res_ed.data:
            edicoes_cadastradas[chave_edicao] = res_ed.data[0]['id']
        else:
            res_nova_ed = supabase.table('edicoes').insert({
                "revista_id": revista_id,
                "volume": chave_edicao,
                "numero": "-", 
                "ano": ano
            }).execute()
            edicoes_cadastradas[chave_edicao] = res_nova_ed.data[0]['id']
            print(f"Nova edição mapeada: {chave_edicao}")

    edicao_id = edicoes_cadastradas[chave_edicao]

    # 4. Inserção do Artigo (Evitando duplicados pelo título)
    res_art = supabase.table('artigos').select('id').eq('titulo', titulo).eq('edicao_id', edicao_id).execute()
    if not res_art.data:
        supabase.table('artigos').insert({
            "edicao_id": edicao_id,
            "titulo": titulo,
            "autores": autores,
            "resumo": resumo[:500] if resumo else None, # Limita tamanho do resumo no teste
            "link_pdf": link_pdf
        }).execute()
        contador += 1

print(f"Processo concluído! {contador} novos artigos inseridos no Supabase.")
