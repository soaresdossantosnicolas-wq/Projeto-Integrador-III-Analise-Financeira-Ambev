// QA visual do aplicativo real. Instale a versão indicada em requirements-qa.txt.
import { chromium } from 'playwright';
import fs from 'node:fs/promises';
const destino = process.env.DASHBOARD_SCREENSHOTS || 'docs/images';
await fs.mkdir(destino, { recursive: true });
const navegador = await chromium.launch({ headless: true });
try {
  const pagina = await navegador.newPage({ viewport: { width: 1440, height: 1050 }, deviceScaleFactor: 1 });
  await pagina.goto('http://127.0.0.1:8501', { waitUntil: 'domcontentloaded' });
  await pagina.getByRole('heading', { name: 'Ambev, em perspectiva.' }).waitFor({ timeout: 60000 });
  await pagina.getByTestId('stPlotlyChart').first().waitFor();
  await pagina.screenshot({ path: `${destino}/dashboard-visao-geral.png`, fullPage: true });
  await pagina.getByRole('tab', { name: 'DRE', exact: true }).click();
  await pagina.getByRole('tab', { name: 'DRE', exact: true }).getAttribute('aria-selected').then(v => { if (v !== 'true') throw new Error('Aba DRE não selecionada'); });
  await pagina.screenshot({ path: `${destino}/dashboard-dre.png`, fullPage: true });
  await pagina.getByRole('tab', { name: 'Projeções', exact: true }).click();
  await pagina.getByRole('heading', { name: 'Projeções exploratórias, com limites explícitos' }).scrollIntoViewIfNeeded();
  await fs.mkdir('docs/img', { recursive: true });
  await pagina.screenshot({ path: 'docs/img/projecoes-anual.png', fullPage: true });
  await pagina.getByLabel('Frequência das projeções').click();
  await pagina.getByRole('option', { name: 'Trimestral · 2026T1–T4', exact: true }).click();
  await pagina.getByText('28 trimestres comparáveis;', { exact: false }).waitFor();
  await pagina.getByRole('heading', { name: 'Projeções exploratórias, com limites explícitos' }).scrollIntoViewIfNeeded();
  await pagina.screenshot({ path: 'docs/img/projecoes-trimestral.png', fullPage: true });
  await pagina.getByRole('tab', { name: 'Sobre', exact: true }).click();
  for (const nome of ['Arthur Almeida', 'Nicolas Soares', 'Pedro Barreto']) {
    await pagina.getByText(nome, { exact: false }).first().waitFor();
  }
  await pagina.getByRole('tab', { name: 'Visão Geral', exact: true }).click();
  const mobile = await navegador.newPage({ viewport: { width: 390, height: 844 } });
  await mobile.goto('http://127.0.0.1:8501');
  await mobile.getByRole('heading', { name: 'Ambev, em perspectiva.' }).waitFor();
  await mobile.getByTestId('stPlotlyChart').first().waitFor();
  await mobile.screenshot({ path: `${destino}/dashboard-mobile.png`, fullPage: true });
  const largura = await mobile.evaluate(() => ({ pagina: document.documentElement.scrollWidth, janela: window.innerWidth }));
  if (largura.pagina > largura.janela) throw new Error('Overflow horizontal na página móvel');
  await pagina.goto('http://127.0.0.1:8502');
  await pagina.getByRole('heading', { name: 'Ambev, em perspectiva.' }).waitFor();
  await pagina.getByTestId('stPlotlyChart').first().waitFor();
  await pagina.screenshot({ path: `${destino}/dashboard-claro.png`, fullPage: true });
  await fs.writeFile(`${destino}/qa-visual.json`, JSON.stringify({ viewportMobile: largura, abas: 8, autoresConferidos: true }, null, 2));
} finally { await navegador.close(); }
