'use strict';
// 示例只提供输入；所有结果由后端调用 Jev 获得。
const demos = {
  noul: {label:'判断', description:'适合有明确是 / 否边界的问题。Jev 返回回答为 true 的概率。', hint:'定义 true / false 各自代表什么', note:'Noul 返回的是概率，而不是布尔值。本页以 0.80 为展示阈值；业务阈值应结合实际样本确定。', examples:[
    {name:'内容审核 · 公开发布', question:'这条消息是否适合公开发布？', context:'大家好！我们将在本周五下午举办产品分享会，欢迎感兴趣的同学报名参加，一起交流使用心得。', criteria:[['true','内容清晰、友好，不包含攻击性或不适合公开的信息。'],['false','包含攻击性、误导性，或不适合公开的敏感信息。']]},
    {name:'客服条件 · 人工接待', question:'客户是否明确要求人工客服？', context:'这是我第三次联系你们了，前两次都没解决。请转人工客服，我要退回这笔订阅费。', criteria:[['true','客户明确提出转人工或由人工客服接待。'],['false','没有明确提出人工接待的要求。']]},
    {name:'会议纪要 · 行动项确认', question:'纪要中是否包含负责人和截止时间都明确的行动项？', context:'会上决定更新展会宣传册。小林负责整理新版文案，周四下班前发给设计组；其他人有建议可以随时补充。', criteria:[['true','至少一项待办同时明确了具体工作、负责人和截止时间。'],['false','没有待办，或所有待办都缺少具体工作、负责人、截止时间中的至少一项。']]},
    {name:'仓储收货 · 验收异常', question:'这批货物是否存在需要登记的验收异常？', context:'采购单订购 50 箱玻璃杯，实际收到 50 箱。抽查时发现其中 3 箱外包装破损，打开后可见杯体裂纹，已拍照留存。', criteria:[['true','收货记录明确出现数量不符、品类不符、破损或质量问题。'],['false','收货记录未报告上述异常，或明确说明验收正常。']]},
    {name:'活动报名 · 材料齐备', question:'这份摄影展报名是否具备初审所需的全部材料？', context:'报名人：陈晨；联系邮箱：chen@example.com；已上传 3 张摄影作品。作品说明栏为空，留言说下周补交。', criteria:[['true','已提供姓名、联系邮箱、至少 3 张作品，以及作品说明，四项缺一不可。'],['false','缺少任意一项必需材料；承诺后补不算已提供。']]},
    {name:'场馆预约 · 时间冲突', question:'新的排练预约是否与现有预约冲突？', context:'同一舞蹈教室周六已有预约：09:00—10:30、14:00—16:00。新申请的时段是周六 10:30—12:00，场馆允许上一场结束后立即开始下一场。', criteria:[['true','新预约与同一场地的已有预约存在实际重叠时段。'],['false','没有实际重叠；仅开始时间等于上一场结束时间不算冲突。']]}
  ]},
  choice: {label:'选择', description:'适合从多个无序选项中选择一类。Jev 返回选中类别及各选项的概率。', hint:'名称和描述均可编辑，都会影响判断，请保持含义一致', note:'Choice 用于分类，选项之间没有高低顺序。图中展示类别概率；最大类别概率不等于 confidence，也不是正确率保证。', examples:[
    {name:'电商售后 · 问题分类', question:'这次售后主要是什么问题？', context:'我买的是黑色耳机，收到的却是白色，请换成黑色，暂时不用退款。', criteria:[['wrong_item','商品型号、颜色或规格与订单不符'],['delivery','物流延误或未收到包裹'],['payment','扣款或账单问题'],['other','其他问题']]},
    {name:'客服分流 · 团队路由', question:'应该由哪个团队处理根本问题？', context:'支付接口一直报错，客户都无法付款，请尽快帮我处理。', criteria:[['technical','系统、接口或软件功能故障'],['billing','扣款、退款或账单争议'],['sales','购买咨询或产品方案'],['other','不属于上述类别']]},
    {name:'旅游规划 · 兴趣分类', question:'这位游客本次旅行最主要的兴趣是什么？', context:'不太想逛商场，也不打算爬山。这次想多看看老建筑和博物馆，最好能预约一场当地历史讲解。吃饭方便就行。', criteria:[['culture','主要关注历史、博物馆、建筑或当地文化'],['nature','主要关注山林、海岛或户外自然风景'],['food','主要关注当地美食和餐饮体验'],['shopping','主要关注购物'],['other','未体现上述兴趣或无法确定主要兴趣']]},
    {name:'校园失物 · 物品归类', question:'这条失物招领应归入哪个物品类别？', context:'今天傍晚在图书馆三楼捡到一把折叠伞，深蓝色，伞柄挂着一只小熊。请失主到一楼服务台认领。', criteria:[['electronics','手机、电脑、耳机等电子设备'],['documents','证件、校园卡或银行卡'],['books','书籍、笔记本或学习资料'],['daily_items','雨伞、水杯、衣物等日常用品'],['other','无法归入上述类别的物品']]},
    {name:'物业报修 · 设施分派', question:'这条报修应按哪个设施类别派单？', context:'三号楼二层走廊的天花板灯一直闪烁，换过灯泡还是一样。水管和电梯都正常，请安排检查照明线路。', criteria:[['lighting','照明灯具、开关或照明线路问题'],['plumbing','供水、漏水或排水管道问题'],['elevator','电梯运行或电梯设备问题'],['access','门禁、门锁或出入口设备问题'],['other','不属于上述设施类别']]},
    {name:'出版编辑 · 稿件栏目', question:'这篇稿件最适合放在哪个栏目？', context:'文章从酵母如何分解糖开始，解释面团发酵时气泡的形成，并设计了不同温度下的对照实验，帮助读者理解发酵原理；没有提供烘焙配方。', criteria:[['science','以解释科学原理或实验现象为主'],['cooking','以食谱、烹饪步骤或厨房技巧为主'],['travel','以目的地介绍或旅行见闻为主'],['arts','以艺术创作、作品欣赏或评论为主'],['other','不属于上述栏目']]}
  ]},
  score: {label:'评分', description:'适合评估程度。标准按顺序从 0 编号，Jev 返回各等级概率的加权分数。', hint:'按程度从低到高排列标准', note:'Score 是有序尺度上的加权位置，可以是小数。它不是百分制成绩，也不是条件成立的概率；不同标准下的分数不应直接比较。', examples:[
    {name:'软件缺陷 · 严重程度', question:'故障对功能使用的影响有多大？', context:'Safari 点击导出 PDF 会报错，但 Chrome 能正常导出。复现步骤：登录后进入报表，选择九月，点击导出。附件有截图和错误日志。', criteria:[['0','只有视觉或文案问题，功能可正常使用'],['1','部分功能不可用，但有可行的替代操作'],['2','核心操作完全受阻，没有可用替代操作']]},
    {name:'软件缺陷 · 报告完整度', question:'报告是否提供足够的排查信息？', context:'Safari 18.0 导出 PDF 时出现 500 错误。步骤：登录 → 进入九月报表 → 点击导出。Chrome 可正常使用，已附错误日志和复现截图。', criteria:[['0','只有笼统描述，没有操作步骤和环境信息'],['1','描述环境或操作步骤，但缺少定位证据'],['2','有明确环境、复现步骤和日志或截图证据']]},
    {name:'教学反馈 · 建议可操作性', question:'这段作文反馈能在多大程度上指导学生修改？', context:'第二段写运动会时只说“大家很激动”，可以补充你看到的动作和听到的声音。例如写起跑前同学握紧接力棒的样子，再写看台上的加油声，让读者感受到现场气氛。', criteria:[['0','只有笼统评价，没有指出修改位置或方向'],['1','指出具体问题或修改方向，但没有说明如何修改'],['2','指出具体位置和问题，并给出可执行的修改方法或示例']]},
    {name:'餐饮评价 · 满意程度', question:'顾客对这次用餐体验的整体满意程度如何？', context:'菜品味道不错，服务员也很耐心，不过预约后还是等了四十分钟，上菜有点慢。整体还可以，但下次会避开周末。', criteria:[['0','整体强烈不满，明确表达糟糕体验或拒绝再次消费'],['1','整体偏不满，负面体验为主'],['2','整体一般或好坏参半，没有明显偏向'],['3','整体满意，正面体验为主，仅有少量不足'],['4','整体非常满意，明确热情推荐或期待再次消费']]},
    {name:'项目策划 · 执行准备度', question:'这份社区读书会方案的执行准备程度如何？', context:'计划下月举办社区读书会，主题和流程已确定。小周负责主持，小陈负责报名，预算为 800 元；场地还在联系，活动日期需等场地方回复后确定。', criteria:[['0','只有活动想法，目标和流程尚未明确'],['1','已明确目标和大致流程，但分工或资源安排尚不明确'],['2','已有流程、分工和预算等安排，但场地、日期等关键条件仍待确认'],['3','流程、分工、预算、场地和日期都已确认，可以按计划执行']]},
    {name:'科普写作 · 公众易读性', question:'这段说明对没有专业背景的读者有多容易理解？', context:'云朵由许多小水滴或小冰晶组成。可以把它想成飘在空中的一大团细雾：水滴非常小，空气的上升运动能托住它们；当水滴聚在一起变得足够大，就可能落下来形成雨。', criteria:[['0','专业术语密集且没有解释，普通读者难以理解'],['1','解释了部分术语，但仍有明显的知识跳跃或复杂表达'],['2','大部分使用日常语言，说明连贯，少量概念仍需背景知识'],['3','用日常语言清楚解释关键概念，并通过恰当例子或类比帮助理解']]}
  ]}
};
// 本地文件默认连接 8765；自定义端口可用 ?api=http://127.0.0.1:8766。
const apiBase = (new URLSearchParams(location.search).get('api') || (location.protocol === 'file:' ? 'http://127.0.0.1:8765' : '')).replace(/\/$/, '');
const $ = id => document.getElementById(id);
const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct = value => `${Math.round(value * 100)}%`;
let mode = 'noul';
let exampleIndex = 0;
let activeRequest;
let lastJSON = '';
function current() { return demos[mode].examples[exampleIndex]; }
function updateContext() {
  const length = $('context').value.length;
  $('char-count').textContent = `${length} 字符`;
  $('context-status').textContent = length && $('context').value.trim() ? '✓ 已填写文本' : '请输入待分析的文本';
}
function setView(view) {
  document.querySelectorAll('[data-view]').forEach(button => {
    const selected = button.dataset.view === view;
    button.setAttribute('aria-selected', String(selected)); button.tabIndex = selected ? 0 : -1;
  });
  $('visual-panel').hidden = view !== 'visual'; $('json-panel').hidden = view !== 'json';
}
function stopRun() {
  activeRequest?.abort(); activeRequest = null;
  $('run').disabled = false; $('run').innerHTML = '运行判断 <span>↗</span>';
}
function clearResult(status = '等待运行') {
  $('result-status').textContent = status;
  $('result-mode').textContent = demos[mode].label;
  $('result-question').textContent = '运行后查看当前输入的模型判断';
  $('result-details').textContent = '';
  $('evaluation').textContent = '填写内容、问题和标准，然后点击“运行判断”。';
  $('reading-note').textContent = demos[mode].note;
  lastJSON = ''; $('json-output').textContent = ''; $('copy-status').textContent = '';
  $('copy-json').disabled = true;
}
function loadExample() {
  stopRun();
  const demo = current();
  $('instructions').value = demo.question; $('context').value = demo.context;
  $('criteria').innerHTML = demo.criteria.map(([key, description], index) => {
    const nameField = mode === 'choice'
      ? `<input id="criterion-key-${index}" class="criterion-key" value="${escapeHTML(key)}" aria-label="第 ${index + 1} 项类别名称" placeholder="类别名称" spellcheck="false">`
      : `<label for="criterion-${index}" class="criterion-tag ${key === 'false' ? 'false' : ''}">${escapeHTML(mode === 'noul' ? key.toUpperCase() : key)}</label>`;
    return `<div class="criterion ${mode === 'choice' ? 'criterion-choice' : ''}">${nameField}<input id="criterion-${index}" class="criterion-description" value="${escapeHTML(description)}" aria-label="第 ${index + 1} 项判定标准" placeholder="类别描述"></div>`;
  }).join('');
  $('edit-note').hidden = true;
  updateContext(); clearResult(); setView('visual');
}
function setMode(next) {
  mode = next; exampleIndex = 0;
  document.querySelectorAll('[data-mode]').forEach(button => {
    const selected = button.dataset.mode === mode;
    button.setAttribute('aria-selected', String(selected)); button.tabIndex = selected ? 0 : -1;
  });
  $('editor').setAttribute('aria-labelledby', `tab-${mode}`);
  $('mode-description').textContent = demos[mode].description;
  $('criteria-hint').textContent = demos[mode].hint;
  $('example').innerHTML = demos[mode].examples.map((item, index) => `<option value="${index}">${escapeHTML(item.name)}</option>`).join('');
  loadExample();
}
function bars(demo) {
  const max = Math.max(...demo.probabilities);
  return demo.probabilities.map((p, index) => `<div class="distribution-row ${p === max ? 'winner' : ''}"><span class="field-key">${escapeHTML(demo.criteria[index][0])}</span><div class="bar-track"><div class="bar-fill" style="--value:${pct(p)}"></div></div><span>${pct(p)}</span></div>`).join('');
}
function renderResult(data) {
  const {answer, input} = data;
  const criteria = Array.isArray(input.criteria) ? input.criteria.map((value, index) => [String(index), value]) : Object.entries(input.criteria);
  const demo = {criteria, value:answer.noul, probabilities:criteria.map(([key]) => answer.probabilities?.[key] ?? 0)};
  $('result-mode').textContent = demos[data.mode].label;
  $('result-question').textContent = input.instructions;
  $('result-details').textContent = `State / context\n${input.state}\n\nCriteria\n${criteria.map(([key, value]) => `${key}: ${value}`).join('\n')}`;
  $('result-status').textContent = `已完成 · ${(data.elapsed_ms / 1000).toFixed(2)} 秒`;
  $('reading-note').textContent = demos[data.mode].note;
  let html = `<div class="card-label"><span>EVALUATION</span><span class="badge">${data.mode.toUpperCase()}</span></div>`;
  if (data.mode === 'noul') {
    const isTrue = answer.noul >= .8;
    const resultProbability = isTrue ? answer.noul : 1 - answer.noul;
    const distribution = {criteria:[['true'], ['false']], probabilities:[answer.noul, 1 - answer.noul]};
    html += `<div class="metric"><strong>${isTrue ? 'TRUE' : 'FALSE'}</strong><span>${pct(resultProbability)}</span></div><div class="distribution-title">true / false 概率分布</div>${bars(distribution)}`;
  } else if (data.mode === 'choice') {
    html += `<div class="metric"><strong class="choice-value">${escapeHTML(answer.choice)}</strong><span>${pct(answer.probabilities[answer.choice])}</span></div><div class="distribution-title">类别概率分布</div>${bars(demo)}`;
  } else {
    const max = criteria.length - 1;
    html += `<div class="metric"><strong>${answer.score.toFixed(2)} <small>/ ${max}</small></strong><span><small>加权分数</small></span></div><div class="bar-track"><div class="bar-fill" style="--value:${pct(answer.score / max)}"></div></div><div class="score-scale">${criteria.map(([key]) => `<span>${escapeHTML(key)}</span>`).join('')}</div><div class="distribution-title">等级概率分布</div>${bars(demo)}`;
  }
  $('evaluation').innerHTML = html;
  lastJSON = JSON.stringify(data, null, 2); $('json-output').textContent = lastJSON;
  $('copy-json').disabled = false; $('copy-status').textContent = '';
}

document.querySelectorAll('[data-mode]').forEach(button => button.addEventListener('click', () => setMode(button.dataset.mode)));
document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => setView(button.dataset.view)));
document.querySelectorAll('[role=tablist]').forEach(list => list.addEventListener('keydown', event => {
  const buttons = [...list.querySelectorAll('[role=tab]')]; const index = buttons.indexOf(document.activeElement);
  if (index < 0 || !['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
  event.preventDefault(); const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length-1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + buttons.length) % buttons.length;
  buttons[next].focus(); buttons[next].click();
}));
$('example').addEventListener('change', () => { exampleIndex = Number($('example').value); loadExample(); });
$('reset').addEventListener('click', loadExample);
$('editor').addEventListener('input', () => {
  stopRun(); updateContext(); clearResult('输入已修改 · 请重新运行');
  $('edit-note').hidden = true;
});
$('run').addEventListener('click', async () => {
  const fields = [$('context'), $('instructions'), ...$('criteria').querySelectorAll('input')];
  const empty = fields.find(field => !field.value.trim());
  if (empty) { $('edit-note').hidden = false; $('edit-note').textContent = empty.classList.contains('criterion-key') ? '请填写类别名称，名称不能只包含空格。' : '请先填写待分析内容、问题和判定标准。'; empty.focus(); return; }
  const keys = [...$('criteria').querySelectorAll('.criterion-key')];
  const seen = new Set();
  for (const input of keys) {
    const key = input.value.trim();
    if (seen.has(key)) {
      $('edit-note').hidden = false; $('edit-note').textContent = `类别名称“${key}”重复，请为每个类别填写不同的名称。`; input.focus(); return;
    }
    seen.add(key);
  }
  stopRun(); clearResult('正在调用 Jev…');
  const controller = new AbortController(); activeRequest = controller;
  const criteria = [...$('criteria').querySelectorAll('.criterion-description')].map((input, index) => [mode === 'choice' ? keys[index].value.trim() : current().criteria[index][0], input.value]);
  const payload = {mode, state:$('context').value, instructions:$('instructions').value,
    criteria:mode === 'score' ? criteria.map(([, value]) => value) : Object.fromEntries(criteria)};
  $('edit-note').hidden = true;
  $('run').disabled = true; $('run').textContent = '判断中…';
  let timedOut = false;
  const timeout = setTimeout(() => { timedOut = true; controller.abort(); }, 70000);
  try {
    const response = await fetch(`${apiBase}/api/evaluate`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload), signal:controller.signal});
    if (!response.headers.get('content-type')?.includes('application/json')) throw new Error(`未连接到实验室后端，请确认 ${apiBase || location.origin} 已启动 FastAPI 服务。`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || '请求失败，请稍后重试。');
    if (activeRequest === controller) renderResult(data);
  } catch (error) {
    if (activeRequest !== controller) return;
    clearResult('运行失败'); $('edit-note').hidden = false;
    $('edit-note').textContent = timedOut ? '请求超时，请检查网络后重试。' : error instanceof TypeError ? `无法连接后端 ${apiBase || location.origin}，请先运行 python -m playground.server。` : error.message;
  } finally {
    clearTimeout(timeout);
    if (activeRequest === controller) stopRun();
  }
});

$('copy-json').addEventListener('click', async () => {
  try { await navigator.clipboard.writeText(lastJSON); $('copy-status').textContent = '已复制 JSON'; }
  catch { $('copy-status').textContent = '当前浏览器无法自动复制，请选中上方 JSON 手动复制。'; }
});
setMode('noul');

async function checkConnection() {
  try {
    const response = await fetch(`${apiBase}/api/health`);
    if (!response.ok) throw new Error();
    const data = await response.json();
    $('api-key').value = data.configured ? '已配置服务端 API Key' : '尚未配置 API Key';
    $('connection-note').textContent = data.configured ? '点击运行后，后端会将输入发送给 Jev 进行判断。' : '请在项目根目录 .env 中设置 TYPESAFE_API_KEY。';
  } catch {
    $('api-key').value = '未连接后端';
    $('connection-note').textContent = `请运行 python -m playground.server，确认后端地址为 ${apiBase || location.origin}，然后刷新页面。`;
  }
}
checkConnection();
