"use strict";
(function (global) {
  function formatSelection(text, start, end, kind) {
    const unchanged = {text, start, end};
    // Do not decorate a selection touching code. Programs must remain literal.
    const before = text.slice(0, start);
    if ((before.match(/^```/gm) || []).length % 2 || ((before.split("\n").pop().match(/`/g)||[]).length % 2)) return unchanged;
    if (text.slice(start, end).includes("`") || !/^(h[123]|bold|italic|highlight|underline)$/.test(kind)) return unchanged;
    if (/^h[123]$/.test(kind)) {
      const lineStart = text.lastIndexOf("\n", start - 1) + 1;
      const next = text.indexOf("\n", end);
      const lineEnd = next < 0 ? text.length : next;
      const selected = text.slice(lineStart, lineEnd).replace(/^#{1,6}\s+/gm, "") || "标题";
      const replacement = selected.split("\n").map(line => `${"#".repeat(Number(kind[1]))} ${line}`).join("\n");
      return {text: text.slice(0,lineStart)+replacement+text.slice(lineEnd),start:lineStart,end:lineStart+replacement.length};
    }
    const pairs = {bold:["**","**"],italic:["*","*"],highlight:["==","=="],underline:["<u>","</u>"]};
    const [left,right] = pairs[kind], selected = text.slice(start,end) || "文字";
    return {text:text.slice(0,start)+left+selected+right+text.slice(end),start:start+left.length,end:start+left.length+selected.length};
  }
  function isRevisionRequest(message, hasReference=false) {
    if (/(不要|不用|别|不需要|无需|不必).{0,12}(改|重做|生成|增加|添加)|如果|是否|能不能|可不可以|是什么意思/.test(message)) return false;
    return (hasReference || /(PPT|讲义|课件|这[一]?页|这节课)/i.test(message)) && /(修改|重做|重新生成|改成|改为|删掉|删除|补充|增加|添加|加.{0,8}(图|代码|例子))/.test(message);
  }
  function createDraft(page, revision) {
    const original = {title:page.title,markdown:page.markdown||"",code:page.code||""};
    let values = {...original};
    return {update(key,value){if(key in original) values[key]=value;},dirty(){return Object.keys(original).some(k=>values[k]!==original[k]);},
      payload(user){return {user_id:user,base_revision:revision,page_id:page.id,...values};},cancel(){values={...original};}};
  }
  function confirmationAction(message,status){
    if(!['proposed','candidate'].includes(status))return null;
    if(/^(取消|保留原版|先不改)[。！!]?$/.test(message.trim()))return 'cancel';
    if(/^(确认|确定)[。！!]?$/.test(message.trim()))return status==='candidate'?'apply':'generate';
    if(status==='proposed'&&/^确认生成修改稿[。！!]?$/.test(message.trim()))return 'generate';
    if(status==='candidate'&&/^(确认修改|应用修改)[。！!]?$/.test(message.trim()))return 'apply';
    return null;
  }
  const exports = {formatSelection,isRevisionRequest,createDraft,confirmationAction};
  if (typeof module !== "undefined") module.exports=exports;
  if (!global.document) return;
  const doc=global.document, byId=id=>doc.getElementById(id);
  const user=global.OnboardingController?.userId || new URLSearchParams(global.location.search).get("user_id") || "yang";
  let manifest=null,page=null,draft=null,busy=false,proposal=null,pendingRestore=null;
  const storageKey=()=>`learning-agent.editor.${user}.${manifest?.lesson_id}.${page?.id}.${manifest?.revision}`;
  const proposalKey=()=>`learning-agent.proposal.${user}.${manifest?.lesson_id}`;
  function notice(text){byId("editorStatus").textContent=text;}
  async function request(path, payload) {
    const res=await fetch(path,payload ? {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)}:undefined);
    const data=await res.json().catch(()=>({}));
    if(!res.ok) throw new Error(typeof data.detail==='string'?data.detail:data.detail?.message||"操作未完成，请保留草稿后重试。");
    return data;
  }
  function setBusy(value){busy=value; byId("lessonEditor").querySelectorAll("button,input,textarea").forEach(n=>n.disabled=value);byId("lessonEditBtn").disabled=value;}
  function preview(){byId("editorPreview").innerHTML=global.MarkdownRenderer.render(byId("editorMarkdown").value);global.MarkdownRenderer.hydrate(byId("editorPreview"));}
  function updateDraft(){if(!draft)return;for(const key of ["title","markdown","code"])draft.update(key,byId(`editor${key[0].toUpperCase()+key.slice(1)}`).value);preview();try{localStorage.setItem(storageKey(),JSON.stringify(draft.payload(user)));}catch{notice("草稿暂存失败，请勿关闭页面。");}}
  function closeEditor(remove=true){if(remove&&draft)localStorage.removeItem(storageKey());draft=null;byId("lessonEditor").hidden=true;byId("lessonPage").hidden=false;byId("lessonEditBtn").textContent="只读 · 编辑";byId("lessonEditBtn").setAttribute("aria-expanded","false");}
  function canLeave(){if(busy)return false;if(draft?.dirty()&&!global.confirm("还有未保存的课件修改。放弃这些修改并离开吗？"))return false;closeEditor();return true;}
  function openEditor(){
    if(!manifest||!page||busy)return;
    if(page.question || page.options?.length){notice("已有选择题请在右侧说明修改要求，确认候选题与答案校验后再应用。");return;}
    draft=createDraft(page,manifest.revision);
    let saved=null;try{saved=JSON.parse(localStorage.getItem(storageKey()));}catch{}
    for(const key of ["title","markdown","code"]){const value=saved?.[key]??page[key]??"";byId(`editor${key[0].toUpperCase()+key.slice(1)}`).value=value;draft.update(key,value);}
    byId("lessonEditor").hidden=false;byId("lessonPage").hidden=true;
    byId("lessonEditBtn").textContent="正在编辑";byId("lessonEditBtn").setAttribute("aria-expanded","true");
    notice(saved?"已恢复本页未保存草稿。":"编辑只影响本页；已有选择题保持只读，可在右侧申请追加新题。");preview();byId("editorTitle").focus();
  }
  async function reload(pageId){const current=await global.ArtifactController.loadCurrentLesson();const i=current.pages.findIndex(p=>p.id===pageId);if(i>=0)global.ArtifactController.showPage(i);await refreshHistory();global.InterviewBankController?.load?.();}
  async function save(){
    if(!draft||busy)return;const payload=draft.payload(user);const key=storageKey();setBusy(true);
    try{await request("/api/lesson/edit",payload);localStorage.removeItem(key);closeEditor(false);await reload(payload.page_id);notice("已保存新版本，可撤销。 ");}
    catch(e){notice(e.message);}finally{setBusy(false);}
  }
  async function refreshHistory(){
    if(!manifest)return;
    try{
      const result=await request(`/api/lesson/edit-state?user_id=${encodeURIComponent(user)}`);
      if(result.lesson?.lesson_id!==manifest.lesson_id)return;
      byId("lessonUndoBtn").disabled=!result.can_undo;
      const list=byId("lessonHistoryList");list.replaceChildren();
      const versions=(result.history||[]).slice().reverse();
      for(const item of versions){
        const row=doc.createElement("div"),text=doc.createElement("span"),button=doc.createElement("button");row.className="lesson-version-row";
        text.textContent=`${({legacy_import:"原始课件",generated:"生成课件",manual_edit:"手动编辑",revision:"教练修改",supplemental:"追加练习",restore:"恢复版本"})[item.reason]||"课件版本"} · ${item.created_at?new Date(item.created_at).toLocaleString():item.revision.slice(0,8)}`;
        button.type="button";button.textContent=item.revision===manifest.revision?"当前版本":"恢复此版本";button.disabled=item.revision===manifest.revision;
        button.addEventListener("click",()=>restore(item.revision));row.append(text,button);list.append(row);
      }
      const previous=versions.find(item=>item.revision!==manifest.revision);
      byId("lessonUndoBtn").onclick=()=>previous&&restore(previous.revision);
    }catch(e){notice(e.message);}
  }
  async function restore(target){
    if(!canLeave())return;
    pendingRestore={baseRevision:manifest.revision,target,pageId:page?.id};
    byId("lessonRestoreDialog").showModal();
  }
  async function confirmRestore(){
    if(!pendingRestore||busy)return;
    const id=pendingRestore.pageId;setBusy(true);byId("lessonRestoreConfirm").disabled=true;byId("lessonRestoreCancel").disabled=true;
    try{await request("/api/lesson/restore",{user_id:user,base_revision:pendingRestore.baseRevision,target_revision:pendingRestore.target});byId("lessonHistoryDialog").close();byId("lessonRestoreDialog").close();pendingRestore=null;await reload(id);notice("课件已恢复，学习记录仍保留。");}
    catch(e){byId("lessonRestoreDialog").close();notice(e.message);}finally{setBusy(false);byId("lessonRestoreConfirm").disabled=false;byId("lessonRestoreCancel").disabled=false;}
  }
  function proposalButton(label,action){const b=doc.createElement("button");b.type="button";b.textContent=label;b.addEventListener("click",action);return b;}
  function renderProposal(value){
    proposal=value;const panel=byId("lessonProposalPanel");panel.hidden=!value;if(!value)return;
    byId("lessonProposalSummary").textContent=(value.summary||"仅生成修改稿，原课件保持不变。")+(value.error?`\n${value.error}`:"");
    byId("lessonProposalStatus").textContent=({proposed:"待确认修改范围",generating:"正在生成候选稿，尚未替换原版",candidate:"候选稿已就绪，请检查后应用",applied:"修改已应用，可从顶部撤销",cancelled:"已取消，原课件未修改",failed:"生成未完成，原课件保持不变"})[value.status]||value.status;
    const actions=byId("lessonProposalActions");actions.replaceChildren();
    if(value.status==='proposed'||value.status==='failed')actions.append(proposalButton("确认生成修改稿",()=>proposalAction("generate")));
    if(value.status==='candidate')actions.append(proposalButton("应用修改",()=>proposalAction("apply")));
    if(!['applied','cancelled'].includes(value.status))actions.append(proposalButton("保留原版 · 取消",()=>proposalAction("cancel")));
    const diff=byId("lessonProposalDiff");diff.replaceChildren();
    for(const change of value.changes||value.changed_pages||[]){
      const section=doc.createElement("details"),summary=doc.createElement("summary"),before=doc.createElement("pre"),after=doc.createElement("pre");
      summary.textContent=change.title||change.page_id||"页面变更";
      before.textContent="原内容\n"+(typeof change.before==='string'?change.before:JSON.stringify(change.before,null,2)||"新增页");
      after.textContent="修改稿\n"+(typeof change.after==='string'?change.after:JSON.stringify(change.after,null,2)||"已移除");
      section.append(summary,before,after);diff.append(section);
    }
  }
  async function propose(instruction,kind="revision",reference=null){
    if(!manifest||!canLeave())return false;
    setBusy(true);
    try{
      const result=await request("/api/lesson/proposals",{user_id:user,base_revision:manifest.revision,instruction,kind,page_id:reference?.page_id||(/这[一]?页/.test(instruction)?page?.id:null)});
      localStorage.setItem(proposalKey(),result.proposal_id);renderProposal(result);byId("lessonProposalPanel").scrollIntoView({block:"nearest"});return true;
    }catch(e){notice(e.message);return false;}finally{setBusy(false);}
  }
  async function proposalAction(action){
    if(busy||!proposal)return;
    if(action==='apply'&&!canLeave())return;
    setBusy(true);const current=proposal,id=page?.id;
    if(action==='generate')renderProposal({...current,status:'generating'});
    byId("lessonProposalActions").querySelectorAll("button").forEach(b=>b.disabled=true);
    try{
      const result=await request(`/api/lesson/proposals/${current.proposal_id}/${action}`,action==='cancel'?{user_id:user}:{user_id:user,confirmed:true});
      if(action==='apply'){renderProposal({...current,status:'applied'});localStorage.removeItem(proposalKey());await reload(id);global.LessonSelection?.clear();}
      else if(action==='cancel'){renderProposal({...current,status:'cancelled'});localStorage.removeItem(proposalKey());}
      else renderProposal({...current,...result});
    }catch(e){
      notice(e.message);
      try{renderProposal(await request(`/api/lesson/proposals/${current.proposal_id}?user_id=${encodeURIComponent(user)}`));}catch{renderProposal(current);}
    }finally{setBusy(false);}
  }
  byId("lessonEditBtn").addEventListener("click",()=>draft?canLeave():openEditor());
  byId("editorSaveBtn").addEventListener("click",save);
  byId("editorCancelBtn").addEventListener("click",()=>canLeave());
  byId("lessonHistoryBtn").addEventListener("click",async()=>{await refreshHistory();byId("lessonHistoryDialog").showModal();});
  byId("lessonHistoryClose").addEventListener("click",()=>byId("lessonHistoryDialog").close());
  byId("lessonRestoreConfirm").addEventListener("click",confirmRestore);
  byId("lessonRestoreCancel").addEventListener("click",()=>{if(busy)return;pendingRestore=null;byId("lessonRestoreDialog").close();});
  byId("lessonRestoreDialog").addEventListener("cancel",event=>{if(busy)event.preventDefault();else pendingRestore=null;});
  byId("lessonExportBtn").addEventListener("click",()=>{global.location.href=`/api/lesson/export?user_id=${encodeURIComponent(user)}`;});
  for(const field of ["editorTitle","editorMarkdown","editorCode"])byId(field).addEventListener("input",updateDraft);
  byId("editorFormatToolbar").querySelectorAll("button").forEach(b=>{
    b.addEventListener("pointerdown",e=>e.preventDefault());
    b.addEventListener("click",()=>{const input=byId("editorMarkdown");const result=formatSelection(input.value,input.selectionStart,input.selectionEnd,b.dataset.format);input.setRangeText(result.text,0,input.value.length,"preserve");input.setSelectionRange(result.start,result.end);input.focus();updateDraft();});
  });
  byId("editorPreviewToggle").addEventListener("click",()=>{const panel=byId("lessonEditor");panel.classList.toggle("preview-only");byId("editorPreviewToggle").textContent=panel.classList.contains("preview-only")?"返回编辑":"预览";});
  global.addEventListener("beforeunload",e=>{if(draft?.dirty()||busy){e.preventDefault();e.returnValue="";}});
  doc.addEventListener("learning-agent:manifest-change",e=>{
    if(manifest?.revision!==e.detail?.revision){closeEditor(false);renderProposal(null);}
    manifest=e.detail;byId("lessonEditBtn").disabled=!manifest;
    refreshHistory();const id=localStorage.getItem(proposalKey());if(id)request(`/api/lesson/proposals/${id}?user_id=${encodeURIComponent(user)}`).then(renderProposal).catch(()=>localStorage.removeItem(proposalKey()));
  });
  doc.addEventListener("learning-agent:page-change",e=>{page=e.detail.page;});
  global.LessonEditor={...exports,propose,canLeave,isBusy:()=>busy,hasDraft:()=>!!draft?.dirty(),isOpen:()=>!!draft,proposalAction,
    pendingConfirmation:message=>confirmationAction(message,proposal?.status)};
})(typeof window!=="undefined"?window:globalThis);
