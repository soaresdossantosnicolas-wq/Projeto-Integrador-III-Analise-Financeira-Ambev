// QA opcional do aplicativo real. Não é dependência do deploy Streamlit.
const {chromium}=require('playwright');
const fs=require('node:fs/promises');
const path=require('node:path');
const abas=['Visão Geral','DRE','Rentabilidade','Liquidez e Endividamento','Balanço','Comparação de Períodos','Projeções','Sobre'];
const fase=process.env.QA_FASE||'depois';
const destino=`outputs/qa-visual/${fase}`;
async function aguardar(p){
  await p.getByRole('heading',{name:'Ambev, em perspectiva.',exact:true}).waitFor({timeout:60000});
  for(let i=0;i<300;i++){
    if(await p.getByTestId('stApp').getAttribute('data-test-script-state')==='notRunning')break;
    await p.waitForTimeout(100);
  }
  if(await p.getByTestId('stException').count())throw Error('Exceção visível no aplicativo: '+(await p.getByTestId('stException').allTextContents()).join(' / '));
}
(async()=>{
 const navegador=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE?{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE}:{}),args:['--no-sandbox']});
 const resultados=[];const verificacoes={};
 try{
  await fs.mkdir(destino,{recursive:true});
  if(!process.env.QA_APENAS_INTERACOES)for(const tema of ['escuro','claro'])for(const dispositivo of ['desktop','celular']){
   const p=await navegador.newPage({viewport:dispositivo==='desktop'?{width:1440,height:1050}:{width:390,height:844},reducedMotion:'reduce'});
   await p.goto(`http://127.0.0.1:${tema==='escuro'?8503:8504}`);
   await aguardar(p);
   await p.locator('[data-testid="stPlotlyChart"] .js-plotly-plot').first().waitFor({state:'visible',timeout:60000});
   await p.getByTestId('stMain').evaluate(e=>e.scrollTop=0);
   await p.screenshot({path:`${destino}/capa-${tema}-${dispositivo}.png`});
   for(let i=0;i<abas.length;i++){
    await p.getByRole('tab',{name:abas[i],exact:true}).click();await aguardar(p);
    if(await p.getByRole('tab',{name:abas[i],exact:true}).getAttribute('aria-selected')!=='true')throw Error('Aba não selecionada');
    if(i<7)await p.locator('[role="tabpanel"]:visible [data-testid="stPlotlyChart"] .js-plotly-plot').first().waitFor({state:'visible',timeout:30000});
    await p.waitForTimeout(350);
    const largura=await p.evaluate(()=>({pagina:document.documentElement.scrollWidth,janela:innerWidth}));
    const kpisTruncados=await p.locator('[data-testid="stMetricValue"], [data-testid="stMetricValue"] *').evaluateAll(es=>es.filter(e=>e.clientWidth>0&&e.scrollWidth>e.clientWidth+1).length);
    if(kpisTruncados)throw Error('Valor de KPI truncado: '+tema+'/'+dispositivo);
    if(largura.pagina>largura.janela)throw Error(`Overflow: ${tema}/${dispositivo}/${abas[i]}`);
    await p.getByTestId('stMain').evaluate(e=>e.scrollTop=0);
    // Mantém a largura e amplia a altura para registrar o conteúdo completo da aba.
    const altura=await p.getByTestId('stMain').evaluate(e=>Math.min(16000,e.scrollHeight+100));
    await p.setViewportSize({width:largura.janela,height:Math.max(altura,dispositivo==='desktop'?1050:844)});
    await p.waitForTimeout(250);
    const arquivo=`${destino}/${tema}-${dispositivo}-${String(i+1).padStart(2,'0')}.png`;
    await p.getByTestId('stMain').evaluate(e=>e.scrollTop=0);
    await p.screenshot({path:arquivo,fullPage:true});
    await p.setViewportSize({width:largura.janela,height:dispositivo==='desktop'?1050:844});
    resultados.push({tema,dispositivo,aba:abas[i],arquivo,largura,excecoes:await p.getByTestId('stException').count()});
   }
   await p.close();
  }
  if(fase==='depois'){
   const p=await navegador.newPage({viewport:{width:1440,height:1050}});
   await p.goto('http://127.0.0.1:8503');await aguardar(p);
   await p.getByRole('button',{name:'Ver contas de 2025',exact:true}).click();
   await p.getByRole('dialog').waitFor();await p.getByText('2025 · da receita ao balanço',{exact:true}).waitFor();
   await p.screenshot({path:`${destino}/detalhamento.png`});
   await p.keyboard.press('Escape');await p.getByRole('dialog').waitFor({state:'hidden'});
   verificacoes.dialogo=true;
   // A seleção é uma interação Plotly real, não uma chamada interna ao Python.
   const ponto=p.locator('[role="tabpanel"]:visible .scatterlayer .point').last();
   await ponto.click({force:true});await p.getByRole('dialog').waitFor({timeout:15000});
   await p.keyboard.press('Escape');await p.getByRole('dialog').waitFor({state:'hidden'});
   verificacoes.selecao_plotly=true;
   await p.locator('[role="tabpanel"]:visible').getByText('Barras',{exact:true}).first().click();await aguardar(p);
   if(await p.getByRole('dialog').isVisible())throw Error('Diálogo reabriu após outro controle');
   verificacoes.selecao_consumida=true;
   await p.getByRole('button',{name:'Exportar dados',exact:true}).click();
   const csv=p.waitForEvent('download');await p.getByRole('button',{name:'CSV · compatível com Excel',exact:true}).click();
   if((await csv).suggestedFilename()!=='ambev_indicadores.csv')throw Error('CSV não disponibilizado');
   await p.waitForTimeout(500);await aguardar(p);if(!(await p.getByRole('button',{name:'Excel · valores numéricos',exact:true}).isVisible()))await p.getByRole('button',{name:'Exportar dados',exact:true}).click();
   const xlsx=p.waitForEvent('download');await p.getByRole('button',{name:'Excel · valores numéricos',exact:true}).click();
   if((await xlsx).suggestedFilename()!=='ambev_indicadores.xlsx')throw Error('Excel não disponibilizado');
   await p.keyboard.press('Escape');verificacoes.downloads=true;
   await p.getByRole('tab',{name:'Projeções',exact:true}).click();await aguardar(p);
   await p.getByLabel('Frequência das projeções',{exact:true}).click();
   await p.getByRole('option',{name:'Trimestral · 2026T1–T4',exact:true}).click();await aguardar(p);
   await p.getByLabel('Cenário',{exact:true}).click();await p.getByRole('option',{name:'Pessimista',exact:true}).click();await aguardar(p);
   const link=p.url();
   const nova=await navegador.newPage();await nova.goto(link);await aguardar(nova);
   if(await nova.getByRole('tab',{name:'Projeções',exact:true}).getAttribute('aria-selected')!=='true')throw Error('Aba não restaurada');
   const cenarioRestaurado=await nova.getByLabel('Cenário',{exact:true}).evaluate(e=>e.value||e.getAttribute('placeholder')||e.innerText);if(!cenarioRestaurado.includes('Pessimista'))throw Error('Cenário não restaurado: '+cenarioRestaurado+' URL: '+link);
   const freqRestaurada=await nova.getByLabel('Frequência das projeções',{exact:true}).evaluate(e=>e.value||e.getAttribute('placeholder')||e.innerText); if(!freqRestaurada.includes('Trimestral'))throw Error('Frequência não restaurada: '+freqRestaurada+' URL: '+link);
   verificacoes.link_compartilhavel=link;await nova.close();
   await p.getByRole('tab',{name:'Visão Geral',exact:true}).click();await aguardar(p);
   await p.getByTestId('stMain').evaluate(e=>e.scrollTop=0);await p.getByText('Modo apresentação',{exact:true}).click();await aguardar(p);
   if(await p.getByTestId('stSidebar').isVisible())throw Error('Sidebar ainda visível no modo apresentação');
   await p.getByTestId('stMain').evaluate(e=>e.scrollTop=0);await p.getByText('Modo apresentação',{exact:true}).click();await aguardar(p);verificacoes.apresentacao=true;
   await p.getByLabel('Aparência',{exact:true}).click();await p.getByRole('option',{name:'Claro',exact:true}).click();await aguardar(p);
   const cor=await p.getByTestId('stApp').evaluate(e=>getComputedStyle(e).backgroundColor);
   if(cor!=='rgb(244, 241, 234)')throw Error(`Tema claro não aplicado: ${cor}`);
   verificacoes.troca_tema=true;await p.close();
  }
  await fs.writeFile(`${destino}/qa.json`,JSON.stringify({capturas:resultados,verificacoes},null,2));
  console.log(JSON.stringify({capturas:resultados.length,excecoes:resultados.filter(r=>r.excecoes).length,verificacoes}));
 }finally{await navegador.close();}
})().catch(e=>{console.error(e.stack);process.exit(1)});
