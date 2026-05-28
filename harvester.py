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

# Dicionário com as revistas alvo e seus respectivos links OAI-PMH
revistas_alvo = {
    "Ciência da Informação (IBICT)": {
        "url": "https://revista.ibict.br/ciinf/oai",
        "area": "Ciência da Informação"
    },
    "Perspectivas em Ciência da Informação (UFMG)": {
        "url": "https://periodicos.letras.ufmg.br/index.php/pci/oai",
        "area": "Ciência da Informação"
    },
    "Acervo (Arquivo Nacional)": {
        "url": "https://revista.arquivonacional.gov.br/index.php/revistaacervo/oai",
        "area": "Arquivologia"
    }
}

for nome_revista, dados in revistas_alvo.items():
    print(f"\n--- Iniciando colheita para: {nome_revista} ---")
    url_oai = dados["url"]
    area_revista = dados["area"]
    
    sickle = Sickle(url_oai)

    # 1. Verifica/Cadastra a Revista
    res_revista = supabase.table('revistas').select('id').eq('nome', nome_revista).execute()
    if not res_revista.data:
        print(f"Cadastrando '{nome_revista}' no banco...")
        res_nova = supabase.table('revistas').insert({
            "nome": nome_revista,
            "area": area_revista
        }).execute()
        revista_id = res_nova.data[0]['id']
    else:
        revista_id = res_revista.data[0]['id']

    edicoes_cadastradas = {}
    edicoes_vistas_nesta_execucao = set() # Memória para contar o limite de 10
    artigos_inseridos = 0

    try:
        # Busca apenas registros publicados a partir de 1º de janeiro de 2025
        records = sickle.ListRecords(metadataPrefix='oai_dc', ignore_deleted=True, from_='2025-01-01')
        
        for record in records:
            metadata = record.metadata
            titulo = metadata.get('title', [''])[0]
            autores = ", ".join(metadata.get('creator', []))
            resumo = metadata.get('description', [''])[0]
            data_pub = metadata.get('date', [''])[0]
            
            identificadores = metadata.get('identifier', [])
            link_pdf = next((link for link in identificadores if 'http' in link), None)
            chave_edicao = metadata.get('source', [''])[0]
            
            if not titulo or not chave_edicao:
                continue
            
            # 2. Lógica do Limite de 10 Edições
            if chave_edicao not in edicoes_vistas_nesta_execucao:
                if len(edicoes_vistas_nesta_execucao) >= 10:
                    print(f"[!] Limite de 10 edições atingido para {nome_revista}.")
                    break # Interrompe a colheita desta revista e vai para a próxima
                edicoes_vistas_nesta_execucao.add(chave_edicao)

            # 3. Gerenciamento da Edição
            if chave_edicao not in edicoes_cadastradas:
                res_ed = supabase.table('edicoes').select('id').eq('volume', chave_edicao).eq('revista_id', revista_id).execute()
                if res_ed.data:
                    edicoes_cadastradas[chave_edicao] = res_ed.data[0]['id']
                else:
                    ano = int(data_pub[:4]) if data_pub and data_pub[:4].isdigit() else 0
                    res_nova_ed = supabase.table('edicoes').insert({
                        "revista_id": revista_id,
                        "volume": chave_edicao,
                        "numero": "-", 
                        "ano": ano
                    }).execute()
                    edicoes_cadastradas[chave_edicao] = res_nova_ed.data[0]['id']
                    print(f"Nova edição mapeada: {chave_edicao}")

            edicao_id = edicoes_cadastradas[chave_edicao]

            # 4. Inserção do Artigo
            res_art = supabase.table('artigos').select('id').eq('titulo', titulo).eq('edicao_id', edicao_id).execute()
            if not res_art.data:
                supabase.table('artigos').insert({
                    "edicao_id": edicao_id,
                    "titulo": titulo,
                    "autores": autores,
                    "resumo": resumo[:1000] if resumo else None,
                    "link_pdf": link_pdf
                }).execute()
                artigos_inseridos += 1
                
    except Exception as e:
        print(f"Erro ao processar o feed de {nome_revista}: {e}")
        
    print(f"Finalizado para {nome_revista}: {artigos_inseridos} novos artigos processados nas 10 primeiras edições.")

print("\n=== Todas as revistas processadas com sucesso! ===")
