// Configuração do cliente Supabase
const SUPABASE_URL = 'https://bhpxcdjmruthjqvfznjp.supabase.co'; 
const SUPABASE_KEY = 'sb_publishable_3PwzTi6zzjTDL6Vpxsz25A_W_vKPvTT';
const _supabase = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

// Mapeamento dos elementos do DOM
const selectRevista = document.getElementById('select-revista');
const selectEdicao = document.getElementById('select-edicao');
const resultadoArtigos = document.getElementById('resultado-artigos');

// 1. Executa ao carregar a página: Busca todas as revistas disponíveis
document.addEventListener('DOMContentLoaded', async () => {
    const { data: revistas, error } = await _supabase
        .from('revistas')
        .select('*')
        .order('nome', { ascending: true });

    if (error) {
        console.error('Erro ao buscar revistas:', error);
        return;
    }

    // Preenche o select de revistas
    revistas.forEach(revista => {
        const option = document.createElement('option');
        option.value = revista.id;
        option.textContent = `${revista.nome} (${revista.area})`;
        selectRevista.appendChild(option);
    });
});

// 2. Executa quando uma revista é selecionada: Busca as edições vinculadas
selectRevista.addEventListener('change', async (e) => {
    const revistaId = e.target.value;
    
    // Limpa e desabilita os campos subsequentes
    selectEdicao.innerHTML = '<option value="">Selecione a Edição...</option>';
    selectEdicao.disabled = true;
    resultadoArtigos.innerHTML = '';

    if (!revistaId) return;

    const { data: edicoes, error } = await _supabase
        .from('edicoes')
        .select('*')
        .eq('revista_id', revistaId)
        .order('ano', { ascending: false });

    if (error) {
        console.error('Erro ao buscar edições:', error);
        return;
    }

    if (edicoes.length > 0) {
        edicoes.forEach(edicao => {
            const option = document.createElement('option');
            option.value = edicao.id;
            option.textContent = `${edicao.volume}, ${edicao.numero} (${edicao.ano})`;
            selectEdicao.appendChild(option);
        });
        selectEdicao.disabled = false;
    }
});

// 3. Executa quando uma edição é selecionada: Gera a lista de artigos em tempo de execução
selectEdicao.addEventListener('change', async (e) => {
    const edicaoId = e.target.value;
    resultadoArtigos.innerHTML = '';

    if (!edicaoId) return;

    const { data: artigos, error } = await _supabase
        .from('artigos')
        .select('*')
        .eq('edicao_id', edicaoId)
        .order('titulo', { ascending: true });

    if (error) {
        console.error('Erro ao buscar artigos:', error);
        return;
    }

    if (artigos.length === 0) {
        resultadoArtigos.innerHTML = '<li class="artigo-item">Nenhum artigo encontrado para esta edição.</li>';
        return;
    }

    // Renderiza cada artigo dinamicamente na tela
    artigos.forEach(artigo => {
        const li = document.createElement('li');
        li.className = 'artigo-item';
        
        li.innerHTML = `
            <h2 class="artigo-titulo">${artigo.titulo}</h2>
            <p class="artigo-autores">${artigo.autores || 'Autor Desconhecido'}</p>
            <p class="artigo-resumo">${artigo.resumo || 'Sem resumo disponível.'}</p>
            ${artigo.link_pdf ? `<a href="${artigo.link_pdf}" target="_blank" class="btn-pdf">Acessar PDF</a>` : ''}
        `;
        
        resultadoArtigos.appendChild(li);
    });
});
