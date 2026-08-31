"use strict";
(function (root) {
  function renderLessonVariant(body, manifest, {document:doc, markdown, i18n}) {
    const heading = (parent, key, level = 'h4') => {
      const label = doc.createElement(level);
      i18n.bind(label, 'textContent', () => i18n.t(key));
      parent.append(label);
    };
    const prose = (parent, value) => {
      const content = doc.createElement('div');
      content.innerHTML = markdown.render(value || '');
      parent.append(content);
    };
    const list = (parent, key, values) => {
      if (!values?.length) return;
      heading(parent, key);
      const items = doc.createElement('ul');
      for (const value of values) { const item = doc.createElement('li'); item.textContent = value; items.append(item); }
      parent.append(items);
    };
    for (const page of manifest.pages || []) {
      const section=doc.createElement('section'), title=doc.createElement('h3');
      section.dataset.pageId=page.id;title.textContent=page.title;section.append(title);
      prose(section,page.markdown);
      if(page.code){const pre=doc.createElement('pre'),code=doc.createElement('code');code.textContent=page.code;pre.append(code);section.append(pre);}
      if(page.question){const question=doc.createElement('p');question.textContent=page.question;section.append(question);
        const options=doc.createElement('ol');for(const option of page.options||[]){const item=doc.createElement('li');item.dataset.optionId=option.id;item.textContent=option.label;options.append(item);}section.append(options);}
      body.append(section);
    }
    if (manifest.completion_prompt) {
      const section=doc.createElement('section');section.className='translation-completion';
      heading(section,'结课说明','h3');prose(section,manifest.completion_prompt);body.append(section);
    }
    if (manifest.interview_prompts?.length) {
      const section=doc.createElement('section');section.className='translation-interview';
      heading(section,'面试表达练习','h3');
      for (const prompt of manifest.interview_prompts) {
        const question=doc.createElement('h4');question.textContent=prompt.question;section.append(question);
        if (prompt.reference_answer) {heading(section,'参考答案','h5');prose(section,prompt.reference_answer);}
        list(section,'回答结构',prompt.answer_structure);
        list(section,'常见遗漏',prompt.common_omissions);
        if (prompt.follow_ups?.length) {
          heading(section,'常见追问');
          for (const followUp of prompt.follow_ups) {
            const question=doc.createElement('p');question.textContent=followUp.prompt;section.append(question);
            list(section,'回答要点',followUp.answer_points);
          }
        }
      }
      body.append(section);
    }
  }
  async function requestTranslation({userId, kind, locale, confirm, fetcher = fetch, sleep = ms => new Promise(resolve => setTimeout(resolve, ms)), onStatus = () => {}}) {
    const query = new URLSearchParams({user_id:userId,kind});
    const read = async (url, options) => {
      const response = await fetcher(url, options);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail?.message || data.detail || 'translation_failed');
      return data;
    };
    const source = await read(`/api/translations/source?${query}`);
    if (!await confirm({kind, locale, source})) return null;
    const accepted = await read('/api/translations/start', {method:'POST',headers:{'Content-Type':'application/json','X-Learning-Locale':locale},body:JSON.stringify({user_id:userId,kind,locale,confirmed:true,source_hash:source.source_hash})});
    const statusQuery = new URLSearchParams({user_id:userId,generation_id:accepted.generation_id});
    for (let poll=0; poll<550; poll++) {
      const job = await read(`/api/translations/status?${statusQuery}`, {headers:{'X-Learning-Locale':locale}});
      onStatus(job.status);
      if (job.status === 'completed') {
        const latest = await read(`/api/translations/source?${query}`);
        if (latest.source_hash !== source.source_hash || job.result?.source_hash !== source.source_hash) throw new Error('source_changed');
        if (!job.result?.ok) throw new Error('translation_failed');
        return job.result;
      }
      if (['failed','cancelled','interrupted'].includes(job.status)) throw new Error(job.result?.detail?.message || 'translation_failed');
      await sleep(1200);
    }
    throw new Error('translation_timeout');
  }
  if (typeof module !== 'undefined') module.exports = {requestTranslation, renderLessonVariant};
  if (!root?.document) return;
  const doc=root.document, i18n=root.LearningI18n, t=(key,params)=>i18n.t(key,params);
  const userId=new URLSearchParams(root.location.search).get('user_id')||'yang';
  let busy=false;
  const dialog=doc.createElement('dialog'); dialog.className='document-dialog translation-dialog';dialog.id='translationDialog';
  const header=doc.createElement('header'), heading=doc.createElement('h2'), close=doc.createElement('button');
  close.type='button';close.className='dialog-close';close.innerHTML='<i class="bi bi-x-lg" aria-hidden="true"></i>';
  i18n.bind(heading,'textContent',()=>t('翻译副本'));
  i18n.bind(close,'@aria-label',()=>t('查看原文'));
  close.addEventListener('click',()=>dialog.close());header.append(heading,close);
  const explanation=doc.createElement('p');explanation.className='translation-context';
  i18n.bind(explanation,'textContent',()=>t('这是只读翻译副本；原文、代码、笔记和作答记录保持不变。关闭即可返回原文。'));
  const body=doc.createElement('article');body.className='markdown-body translation-content';
  dialog.append(header,explanation,body);doc.body.append(dialog);
  dialog.addEventListener('click',event=>{if(event.target===dialog)dialog.close();});
  function renderVariant(result) {
    body.replaceChildren();body.lang=result.locale;
    if(result.kind==='plan')body.innerHTML=root.MarkdownRenderer.render(result.content);
    else renderLessonVariant(body,result.content,{document:doc,markdown:root.MarkdownRenderer,i18n});
    root.MarkdownRenderer.hydrate(body);dialog.showModal();
  }
  function mountAction(kind, parent) {
    if(!parent)return;
    const row=doc.createElement('div');row.className='translation-tools';
    const button=doc.createElement('button');button.type='button';button.id=kind==='plan'?'translatePlanBtn':'translateLessonBtn';
    const status=doc.createElement('span');status.setAttribute('role','status');
    i18n.bind(button,'textContent',()=>t(kind==='plan'?'翻译当前 Plan':'翻译当前章课件'));
    button.addEventListener('click',async()=>{
      if(busy)return;
      const locale=i18n.getLocale();busy=true;button.disabled=true;
      i18n.bind(status,'textContent',()=>t('正在准备翻译副本，原文不会被修改。'));
      try {
        const result=await requestTranslation({userId,kind,locale,fetcher:root.fetch,
          confirm:()=>root.confirm(t('仅将{0}翻译为{1}并保存副本，可能需要模型调用。不会翻译历史聊天或其他章节。继续吗？',{0:t(kind==='plan'?'当前 Plan':'当前章课件'),1:locale==='en'?'English':'中文'}))});
        if(result){renderVariant(result);i18n.bind(status,'textContent',()=>t('翻译副本已就绪；原文保持不变。'));}
        else status.textContent='';
      } catch(error) {
        i18n.bind(status,'textContent',()=>error.message==='source_changed'?t('原文已经变化，这份译本未显示。请重新翻译当前版本。'):t('翻译未完成，原文保持不变。可以重试；详细原因见诊断报告。'));
      } finally {busy=false;button.disabled=false;}
    });
    row.append(button,status);parent.append(row);
    return row;
  }
  const planHost=doc.getElementById('planDialog');
  if(planHost){const mount=doc.createElement('div');planHost.insertBefore(mount,doc.getElementById('planDocument'));mountAction('plan',mount);}
  const lessonHost=doc.querySelector('.artifact-topbar');
  if(lessonHost){const mount=doc.createElement('div');lessonHost.insertAdjacentElement('afterend',mount);const row=mountAction('lesson',mount);row.hidden=true;
    doc.addEventListener('learning-agent:manifest-change',event=>{row.hidden=!event.detail;});}
  // Closing the read-only overlay restores the exact original view; no lesson state is replaced.
}(typeof window==='undefined'?null:window));
