/**
 * Nexus Flow — Jarvis AI Development Assistant
 * Upgraded: workspace, modes, project context, voice, model selector, actions.
 */
(function () {
  'use strict';
  const API = '/api/jarvis';
  let state = { projectId: null, mode: 'chat', isLoading: false, isListening: false };
  let recognition = null;
  let els = {};

  function init() {
    els.chatLog = document.getElementById('jvChatLog');
    els.input = document.getElementById('jvInput');
    els.sendBtn = document.getElementById('jvSendBtn');
    els.voiceBtn = document.getElementById('jvVoiceBtn');
    els.modeTabs = document.querySelectorAll('.jv-mode-btn');
    els.projectSelect = document.getElementById('jvProjectSelect');
    els.fileList = document.getElementById('jvFileList');
    els.ctxFramework = document.getElementById('jvCtxFramework');
    els.ctxFiles = document.getElementById('jvCtxFiles');
    els.ctxModel = document.getElementById('jvCtxModel');
    els.ctxProject = document.getElementById('jvCtxProject');
    els.wsProjectName = document.getElementById('jvWsProjectName');
    els.modelSelect = document.getElementById('jvModelSelect');
    els.modelStatus = document.getElementById('jvModelStatus');
    els.modelBadge = document.getElementById('jvModelBadge');
    els.analysisCard = document.getElementById('jvAnalysisCard');
    els.analysisContent = document.getElementById('jvAnalysisContent');
    els.fileCount = document.getElementById('jvFileCount');
    // New Cursor-like workspace elements
    els.centerSub = document.getElementById('jvCenterSub');
    els.topStatus = document.getElementById('jvTopStatus');
    els.topModel = document.getElementById('jvTopModel');
    els.topProject = document.getElementById('jvTopProject');
    els.currentTask = document.getElementById('jvCurrentTask');
    els.statusOnline = document.getElementById('jvStatusOnline');
    els.ctxTask = document.getElementById('jvCtxTask');
    els.ctxModelDup = document.getElementById('jvCtxModelDup');
    els.currentFileLabel = document.getElementById('jvCurrentFileLabel');
    els.currentFilePath = document.getElementById('jvCurrentFilePath');
    els.codeDiff = document.getElementById('jvCodeDiff');
    els.codePreview = document.getElementById('jvCodePreview');
    els.codeContent = document.getElementById('jvCodeContent');
    els.applyBtn = document.getElementById('jvApplyBtn');
    els.revertBtn = document.getElementById('jvRevertBtn');
    els.recentChanges = document.getElementById('jvRecentChanges');
    els.changesCount = document.getElementById('jvChangesCount');
    els.issuesList = document.getElementById('jvIssuesList');
    els.issuesCount = document.getElementById('jvIssuesCount');
    els.approvalModal = document.getElementById('jvApprovalModal');
    els.approvalBody = document.getElementById('jvApprovalBody');
    els.approveBtn = document.getElementById('jvApproveBtn');
    els.rejectBtn = document.getElementById('jvRejectBtn');

    // Project id from URL or storage
    const params = new URLSearchParams(window.location.search);
    const urlPid = params.get('project_id') || params.get('projectId');
    const stored = localStorage.getItem('jarvis_last_project');
    state.projectId = urlPid || stored || null;

    bindEvents();
    loadProjects();
    loadModels();
    checkHealth();
    loadMemory();
    if (state.projectId) loadContext(state.projectId);
    initVoice();
  }

  let pendingApproval = null;
  let recentChangesList = [];
  let currentFile = null;
  let lastFileContent = '';

  function setTask(task){ if(els.currentTask) els.currentTask.textContent = task; if(els.ctxTask) els.ctxTask.textContent = task; }
  function updateTopBar(){
    if(els.topModel) els.topModel.textContent = (els.modelBadge? els.modelBadge.textContent : 'Llama 3.3');
    if(els.topProject) els.topProject.textContent = (els.wsProjectName? els.wsProjectName.textContent : 'No project');
    if(els.topStatus) els.topStatus.textContent = 'Online';
  }

  function bindEvents() {
    if (els.sendBtn) els.sendBtn.addEventListener('click', sendMessage);
    if (els.input) {
      els.input.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
      });
      els.input.addEventListener('input', function(){ this.style.height='auto'; this.style.height=Math.min(this.scrollHeight,120)+'px';});
    }
    els.modeTabs.forEach(b=>b.addEventListener('click', ()=>{
      els.modeTabs.forEach(x=>x.classList.remove('active'));
      b.classList.add('active');
      state.mode = b.dataset.mode;
      addSystemNote('Mode: ' + state.mode);
      if(els.centerSub) els.centerSub.textContent = state.mode.charAt(0).toUpperCase()+state.mode.slice(1);
      if(state.mode==='changes') renderRecentChanges();
      if(state.mode==='analyze') doAnalyze();
      if(state.mode==='debug') addBubble('Debug mode: describe the error or check preview logs.', 'assistant');
      setTask(state.mode);
      updateTopBar();
    }));
    if (els.projectSelect) els.projectSelect.addEventListener('change', e=>{
      state.projectId = e.target.value || null;
      if(state.projectId) localStorage.setItem('jarvis_last_project', state.projectId);
      loadContext(state.projectId);
      loadMemory();
    });
    if (els.voiceBtn) els.voiceBtn.addEventListener('click', toggleVoice);
    document.querySelectorAll('.jv-quick').forEach(b=>b.addEventListener('click', ()=>{
      els.input.value = b.dataset.prompt;
      sendMessage();
    }));
    // Workspace actions (Command Center)
    const btnAnalyze = document.getElementById('btnAnalyze');
    const btnFix = document.getElementById('btnFix');
    const btnExplain = document.getElementById('btnExplain');
    const btnModify = document.getElementById('btnModify');
    const btnRunTest = document.getElementById('btnRunTest');
    const btnImproveDesign = document.getElementById('btnImproveDesign');
    const btnOptimize = document.getElementById('btnOptimize');
    const btnDeploy = document.getElementById('btnDeploy');
    if(btnAnalyze) btnAnalyze.addEventListener('click', doAnalyze);
    if(btnFix) btnFix.addEventListener('click', doFix);
    if(btnExplain) btnExplain.addEventListener('click', doExplain);
    if(btnModify) btnModify.addEventListener('click', ()=> showModify(true));
    if(btnRunTest) btnRunTest.addEventListener('click', doRunTest);
    if(btnImproveDesign) btnImproveDesign.addEventListener('click', ()=>{ addBubble('Improving design...','user'); fetch(API+'/modify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id: state.projectId, request: 'Improve design: make it more modern, better spacing, glassmorphism'})}).then(handleJson).then(d=> handleModifyResponse(d)); });
    if(btnOptimize) btnOptimize.addEventListener('click', ()=>{ addBubble('Optimizing code...','user'); fetch(API+'/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id: state.projectId})}).then(handleJson).then(d=>{ addBubble('Optimization suggestions: '+(d.suggestions||[]).join('; '),'assistant'); renderIssues(d.issues||[]);}); });
    if(btnDeploy) btnDeploy.addEventListener('click', ()=>{ if(!state.projectId) return addBubble('Select a project first.','assistant'); window.location.href='/download/zip/'+encodeURIComponent(state.projectId); });
    // Code assistant
    if(els.applyBtn) els.applyBtn.addEventListener('click', applyPending);
    if(els.revertBtn) els.revertBtn.addEventListener('click', revertPending);
    // Approval workflow
    const apprClose = document.getElementById('jvApprovalClose');
    if(apprClose) apprClose.addEventListener('click', hideApproval);
    if(els.approveBtn) els.approveBtn.addEventListener('click', applyPending);
    if(els.rejectBtn) els.rejectBtn.addEventListener('click', hideApproval);
    if(els.approvalModal) els.approvalModal.addEventListener('click', e=>{ if(e.target===els.approvalModal) hideApproval(); });
    // Modify modal
    const mClose = document.getElementById('jvModifyClose');
    const mCancel = document.getElementById('jvModifyCancel');
    const mSubmit = document.getElementById('jvModifySubmit');
    if(mClose) mClose.addEventListener('click', ()=> showModify(false));
    if(mCancel) mCancel.addEventListener('click', ()=> showModify(false));
    if(mSubmit) mSubmit.addEventListener('click', submitModify);
    if(els.modelSelect) els.modelSelect.addEventListener('change', onModelChange);
  }

  // ---------- Projects ----------
  function loadProjects(){
    fetch(API+'/projects').then(r=>r.json()).then(data=>{
      if(!data.success || !els.projectSelect) return;
      els.projectSelect.innerHTML='<option value=\"\">No project selected</option>';
      (data.projects||[]).forEach(p=>{
        const o=document.createElement('option');
        o.value=p.id; o.textContent=p.title + ' — ' + (p.prompt||'').slice(0,40);
        if(p.id===state.projectId) o.selected=true;
        els.projectSelect.appendChild(o);
      });
      if(!state.projectId && data.projects && data.projects[0]){
        // auto select first
        state.projectId = data.projects[0].id;
        els.projectSelect.value = state.projectId;
        localStorage.setItem('jarvis_last_project', state.projectId);
        loadContext(state.projectId);
      }
      updateWsHeader();
    }).catch(()=>{});
  }

  function loadContext(pid){
    if(!pid){
      if(els.ctxFramework) els.ctxFramework.textContent='—';
      if(els.ctxFiles) els.ctxFiles.textContent='—';
      if(els.ctxProject) els.ctxProject.textContent='—';
      if(els.wsProjectName) els.wsProjectName.textContent='No project';
      if(els.fileList) els.fileList.innerHTML='<div class=\"jv-empty\">Select a project to see files</div>';
      if(els.fileCount) els.fileCount.textContent='0';
      return;
    }
    fetch(API+'/context?project_id='+encodeURIComponent(pid)).then(r=>r.json()).then(data=>{
      if(!data.success) return;
      const ctx = data.context || {};
      if(els.ctxFramework) els.ctxFramework.textContent = ctx.framework || 'Unknown';
      if(els.ctxFiles) els.ctxFiles.textContent = (ctx.file_count||0)+' files';
      if(els.fileCount) els.fileCount.textContent = ctx.file_count||0;
      if(els.ctxProject) els.ctxProject.textContent = (ctx.project && ctx.project.title) || pid.slice(0,8);
      if(els.wsProjectName) els.wsProjectName.textContent = (ctx.project && ctx.project.title) || 'Project '+pid.slice(0,6);
      if(els.fileList){
        const files = ctx.files || [];
        if(!files.length) els.fileList.innerHTML='<div class=\"jv-empty\">No files found</div>';
        else els.fileList.innerHTML = files.slice(0,25).map(f=>{
          const icon = f.endsWith('.css')?'fa-css3': f.endsWith('.js')?'fa-js': f.endsWith('.html')?'fa-html5':'fa-file';
          return '<div class=\"jv-file-item\" data-file=\"'+esc(f)+'\"><i class=\"fa-brands '+icon+'\"></i> '+esc(f)+'</div>';
        }).join('');
        els.fileList.querySelectorAll('.jv-file-item').forEach(el=>el.addEventListener('click', ()=>{
          const fp = el.dataset.file;
          els.input.value = 'Explain code in '+fp;
          els.input.focus();
          // Update Code Assistant panel
          if(els.currentFileLabel) els.currentFileLabel.textContent = fp;
          if(els.currentFilePath) els.currentFilePath.textContent = fp;
          // Try to show file content from context
          const content = (ctx.files_content && ctx.files_content[fp]) || '(loading...)';
          if(els.codePreview){
            els.codePreview.style.display='block';
            if(els.codeContent) els.codeContent.textContent = content.slice(0,4000);
          }
          if(els.codeDiff) els.codeDiff.innerHTML='<div class="jv-empty">Selected: '+esc(fp)+'</div>';
          currentFile = fp;
        }));
      }
      // Update status & top bar
      if(els.statusOnline) els.statusOnline.textContent='● Online';
      const dot = document.getElementById('jvStatusDot'); if(dot) dot.className='jv-status-dot online';
      updateTopBar();
    });
  }

  function updateWsHeader(){
    const sel = els.projectSelect && els.projectSelect.options[els.projectSelect.selectedIndex];
    if(els.wsProjectName && sel) els.wsProjectName.textContent = sel.textContent.split(' — ')[0] || 'No project';
    if(els.topProject) els.topProject.textContent = (sel? sel.textContent.split(' — ')[0] : 'No project');
    if(els.topModel && els.modelBadge) els.topModel.textContent = els.modelBadge.textContent;
  }

  // ---------- Cursor-like helpers ----------
  function renderRecentChanges(){
    if(!els.recentChanges) return;
    if(!recentChangesList.length){
      els.recentChanges.innerHTML='<div class="jv-empty">No changes yet. Jarvis will log edits here.</div>';
      if(els.changesCount) els.changesCount.textContent='0';
      return;
    }
    if(els.changesCount) els.changesCount.textContent=String(recentChangesList.length);
    els.recentChanges.innerHTML = recentChangesList.slice(-8).reverse().map(c=> '<div class="jv-recent-item"><i class="fa-solid fa-code-branch"></i><span>'+esc(c.file)+'</span><span style="margin-left:auto;color:#64748b;font-size:11px">'+esc(c.time)+'</span></div>').join('');
  }
  function addRecentChange(file, reason){
    recentChangesList.push({file:file, reason:reason||'AI edit', time: new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})});
    renderRecentChanges();
  }
  function renderIssues(issues){
    if(els.issuesCount) els.issuesCount.textContent = String((issues||[]).length);
    if(!els.issuesList) return;
    if(!issues || !issues.length){
      els.issuesList.innerHTML='<div class="jv-empty">No issues detected. Run Analyze.</div>';
      return;
    }
    els.issuesList.innerHTML = issues.slice(0,12).map(i=>{
      const cls = (i.type==='error'?'error':'warning');
      return '<div class="jv-issue-item '+cls+'"><strong>'+esc(i.message||i.issue||'Issue')+'</strong><div style="color:#94a3b8;font-size:11px">'+esc(i.file||'')+'</div></div>';
    }).join('');
  }
  function showDiff(file, oldContent, newContent){
    els.currentFilePath = els.currentFilePath || document.getElementById('jvCurrentFilePath');
    if(els.currentFilePath) els.currentFilePath.textContent = file;
    if(els.currentFileLabel) els.currentFileLabel.textContent = file;
    currentFile = file;
    lastFileContent = oldContent||'';
    if(!els.codeDiff) return;
    // Simple line diff
    const oldLines = (oldContent||'').split('\n');
    const newLines = (newContent||'').split('\n');
    const max = Math.max(oldLines.length, newLines.length);
    let html='';
    for(let i=0;i<max;i++){
      const o = oldLines[i]; const n = newLines[i];
      if(o===n){ if(o!==undefined) html+='<div class="jv-diff-line jv-diff-ctx">'+esc(o)+'</div>'; }
      else {
        if(o!==undefined) html+='<div class="jv-diff-line jv-diff-del">- '+esc(o)+'</div>';
        if(n!==undefined) html+='<div class="jv-diff-line jv-diff-add">+ '+esc(n)+'</div>';
      }
    }
    if(!html) html='<div class="jv-empty">No diff available</div>';
    els.codeDiff.innerHTML = html;
    if(els.codePreview) els.codePreview.style.display='none';
    if(els.applyBtn) els.applyBtn.style.display='inline-flex';
    if(els.revertBtn) els.revertBtn.style.display='inline-flex';
    // Also show in preview
    if(els.codeContent){ els.codeContent.textContent = newContent||''; }
  }
  function showApproval(data){
    // data: {files_changed, fixed_files, explanation, reason}
    pendingApproval = data;
    const files = data.files_changed || Object.keys(data.fixed_files||{});
    const reason = data.explanation || data.reason || 'AI proposed changes';
    let html='<div class="jv-approval-meta">Reason: '+esc(reason)+'</div>';
    html+='<div style="display:flex;gap:12px;font-size:12px;color:#94a3b8"><span>Files: '+files.length+'</span><span>Lines: ~'+Object.values(data.fixed_files||{}).reduce((a,v)=>a+(v.split("\n").length),0)+'</span></div>';
    files.forEach(f=>{
      const content = (data.fixed_files||{})[f]||'';
      html+='<div class="jv-approval-file"><div class="jv-approval-file-head"><span>'+esc(f)+'</span><span class="jv-approval-meta">'+content.split("\n").length+' lines</span></div><pre style="margin:0;padding:8px;max-height:120px;overflow:auto;font-size:11px;background:rgba(0,0,0,0.3);color:#cbd5e1">'+esc(content.slice(0,600))+'</pre></div>';
    });
    if(els.approvalBody) els.approvalBody.innerHTML = html;
    if(els.approvalModal) els.approvalModal.style.display='flex';
    // Also push to center diff
    const first = files[0];
    if(first && data.fixed_files && data.fixed_files[first]){
      // Try to fetch old content
      fetch('/api/builder/project/'+encodeURIComponent(state.projectId||'')).then(r=>r.json()).then(j=>{
        const old = (j.files && j.files[first]) || '';
        showDiff(first, old, data.fixed_files[first]);
      }).catch(()=> showDiff(first, '', data.fixed_files[first]));
    }
  }
  function hideApproval(){ if(els.approvalModal) els.approvalModal.style.display='none'; pendingApproval=null; }
  function applyPending(){
    if(!pendingApproval) return;
    // Apply via existing jarvis apply endpoint or direct
    const payload = {project_id: state.projectId, fixed_files: pendingApproval.fixed_files};
    // Use new endpoint if available else fallback to modify's implied apply already done
    fetch(API+'/apply', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
      .then(handleJson).then(d=>{
        if(d.success!==false){
          hideApproval();
          addBubble('Changes applied: '+(pendingApproval.files_changed||[]).join(', '),'assistant');
          (pendingApproval.files_changed||[]).forEach(f=> addRecentChange(f, pendingApproval.explanation||'Apply'));
          loadContext(state.projectId);
          if(els.applyBtn) els.applyBtn.style.display='none';
          if(els.revertBtn) els.revertBtn.style.display='none';
          pendingApproval=null;
        } else {
          addBubble('Apply failed: '+(d.error||''),'assistant');
        }
      }).catch(e=>{ // fallback: assume already applied via fix flow
        hideApproval();
        addBubble('Approved (local): '+(pendingApproval.files_changed||[]).join(', '),'assistant');
        pendingApproval=null;
      });
  }
  function revertPending(){
    hideApproval();
    pendingApproval=null;
    if(els.codeDiff) els.codeDiff.innerHTML='<div class="jv-empty">Reverted. No pending changes.</div>';
    if(els.applyBtn) els.applyBtn.style.display='none';
    if(els.revertBtn) els.revertBtn.style.display='none';
    addBubble('Changes rejected.','assistant');
  }
  function handleModifyResponse(d){
    if(!d.success) return addBubble('Modify failed: '+(d.error||''),'assistant');
    // Show approval workflow
    const filesChanged = d.files_changed || Object.keys(d.fixed_files||{});
    if(filesChanged.length){
      showApproval({files_changed: filesChanged, fixed_files: d.fixed_files||{}, explanation: d.explanation||'AI modification', reason: d.explanation});
      filesChanged.forEach(f=> addRecentChange(f, d.explanation||'Modify'));
    } else {
      addBubble(d.explanation||'Modified','assistant');
    }
  }

  // ---------- Models ----------
  function loadModels(){
    fetch(API+'/models').then(r=>r.json()).then(data=>{
      if(!data.success) return;
      const active = data.active || {};
      if(els.ctxModel) els.ctxModel.textContent = (active.provider||'') + '/' + (active.model||'');
      if(els.modelBadge) els.modelBadge.textContent = active.model || 'Llama 3.3';
      if(!els.modelSelect) return;
      const models = data.models || {};
      els.modelSelect.innerHTML='';
      Object.keys(models).forEach(k=>{
        const m = models[k];
        const o=document.createElement('option');
        o.value = m.provider+'|'+m.model;
        o.textContent = m.provider+' / '+m.model + (m.is_active?' ●':'');
        if(m.is_active) o.selected=true;
        els.modelSelect.appendChild(o);
      });
      if(els.modelStatus) els.modelStatus.textContent = (active.provider? 'Active: '+active.provider+'/'+active.model : 'No active model');
    }).catch(()=>{});
  }
  function onModelChange(e){
    const v = e.target.value; // provider|model
    const [provider, model] = v.split('|');
    fetch(API+'/model/select',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider, model})})
      .then(r=>r.json()).then(d=>{
        if(d.success){ if(els.modelStatus) els.modelStatus.textContent='Switched to '+provider+'/'+model; if(els.ctxModel) els.ctxModel.textContent=provider+'/'+model; if(els.modelBadge) els.modelBadge.textContent=model; }
        else { if(els.modelStatus) els.modelStatus.textContent='Failed: '+(d.error||''); }
      });
  }

  // ---------- Memory ----------
  function loadMemory(){
    const pid = state.projectId || '';
    fetch(API+'/memory?project_id='+encodeURIComponent(pid)).then(r=>r.json()).then(data=>{
      if(data.success && data.memory && data.memory.conversation_history && data.memory.conversation_history.length){
        // Optionally restore history - show last 6
        const h = data.memory.conversation_history.slice(-6);
        // Clear welcome
        const w = els.chatLog.querySelector('.jv-welcome');
        if(w && h.length) w.remove();
        h.forEach(entry=>{
          if(entry.role==='user' || entry.role==='assistant'){
            addBubble(entry.content, entry.role==='user'?'user':'assistant', false);
          }
        });
      }
    }).catch(()=>{});
  }

  // ---------- Health & Status ----------
  function checkHealth(){
    fetch(API+'/health').then(r=>r.json()).then(d=>{
      console.log('[Jarvis] health',d);
      const online = d.status==='online' || d.success;
      if(els.statusOnline) els.statusOnline.textContent = online? '● Online' : '● Offline';
      const dot = document.getElementById('jvStatusDot');
      if(dot) dot.className = online? 'jv-status-dot online' : 'jv-status-dot offline';
      if(els.topStatus) els.topStatus.textContent = online? 'Online' : 'Offline';
      if(d.provider && els.ctxModel) els.ctxModel.textContent = d.provider + (d.model? '/'+d.model:'');
      if(els.topModel && d.model) els.topModel.textContent = d.model;
      if(els.ctxModelDup && d.provider) els.ctxModelDup.textContent = d.provider + (d.model? '/'+d.model:'');
      setTask(online? 'Idle' : 'Offline');
      updateTopBar();
    }).catch(()=>{
      if(els.statusOnline) els.statusOnline.textContent='● Offline';
    });
  }

  // ---------- Voice ----------
  function initVoice(){
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if(!SR) { if(els.voiceBtn) els.voiceBtn.style.display='none'; return; }
    recognition = new SR();
    recognition.continuous=false; recognition.interimResults=false; recognition.lang='en-US';
    recognition.onstart = ()=>{ state.isListening=true; if(els.voiceBtn) els.voiceBtn.classList.add('listening'); const h=document.getElementById('jvListeningHint'); if(h) h.style.display='inline'; };
    recognition.onend = ()=>{ state.isListening=false; if(els.voiceBtn) els.voiceBtn.classList.remove('listening'); const h=document.getElementById('jvListeningHint'); if(h) h.style.display='none'; };
    recognition.onresult = (e)=>{
      const t = e.results[0][0].transcript;
      if(els.input){ els.input.value = t; els.input.focus(); }
    };
    recognition.onerror = ()=>{ state.isListening=false; if(els.voiceBtn) els.voiceBtn.classList.remove('listening'); };
  }
  function toggleVoice(){
    if(!recognition) return;
    if(state.isListening) recognition.stop();
    else try{ recognition.start(); }catch(e){}
  }

  // ---------- Chat ----------
  function sendMessage(){
    const text = (els.input.value||'').trim();
    if(!text || state.isLoading) return;
    els.input.value=''; els.input.style.height='auto';
    const welcome = els.chatLog.querySelector('.jv-welcome');
    if(welcome) welcome.remove();
    addBubble(text,'user');
    showTyping();
    state.isLoading=true; if(els.sendBtn) els.sendBtn.disabled=true;
    const payload = { message: text, project_id: state.projectId, mode: state.mode };
    fetch(API+'/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
      .then(handleJson).then(data=>{
        hideTyping(); state.isLoading=false; if(els.sendBtn) els.sendBtn.disabled=false;
        if(data.success){
          addBubble(data.response,'assistant');
          if(data.suggestions && data.suggestions.length) addSuggestions(data.suggestions);
          if(data.files_changed && data.files_changed.length) addSystemNote('Files changed: '+data.files_changed.join(', '));
          if(data.project_context) loadContext(state.projectId);
        } else {
          addBubble(data.error||'Something went wrong','assistant');
        }
      }).catch(err=>{
        hideTyping(); state.isLoading=false; if(els.sendBtn) els.sendBtn.disabled=false;
        addBubble('Connection error: '+err.message,'assistant');
      });
  }

  function handleJson(res){
    const ct=res.headers.get('content-type')||'';
    if(!res.ok) return res.text().then(t=>{ try{const j=JSON.parse(t); throw new Error(j.error||'Server error '+res.status);}catch(e){ if(e instanceof SyntaxError) throw new Error('Server unavailable'); throw e; }});
    if(!ct.includes('application/json')) return res.text().then(()=>{ throw new Error('Invalid response'); });
    return res.json();
  }

  function addBubble(text, role, scroll=true){
    const wrap=document.createElement('div');
    wrap.className='jv-bubble jv-bubble-'+role;
    const icon=role==='user'?'fa-user':'fa-robot';
    const name=role==='user'?'You':'Jarvis';
    const time=new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});
    // simple markdown for code blocks
    let html = escHtml(text);
    html = html.replace(/```([\s\S]*?)```/g, (m,c)=>'<pre><code>'+escHtml(c)+'</code></pre>');
    html = html.replace(/\n/g,'<br>');
    wrap.innerHTML='<div class=\"jv-bubble-avatar\"><i class=\"fa-solid '+icon+'\"></i></div><div class=\"jv-bubble-body\"><div class=\"jv-bubble-name\">'+name+'</div><div class=\"jv-bubble-text\">'+html+'</div><div class=\"jv-bubble-time\">'+time+'</div></div>';
    els.chatLog.appendChild(wrap);
    if(scroll) scrollChat();
  }
  function addSystemNote(t){
    const d=document.createElement('div');
    d.style.cssText='align-self:center;background:rgba(99,102,241,0.12);border:1px solid rgba(99,102,241,0.2);color:#a5b4fc;font-size:12px;padding:6px 12px;border-radius:999px;margin:6px 0';
    d.textContent=t;
    els.chatLog.appendChild(d);
    scrollChat();
  }
  function addSuggestions(arr){
    const wrap=document.createElement('div');
    wrap.style.cssText='display:flex;gap:6px;flex-wrap:wrap;align-self:flex-start;margin-left:42px';
    arr.slice(0,3).forEach(s=>{
      const b=document.createElement('button');
      b.className='jv-quick'; b.textContent=s; b.onclick=()=>{els.input.value=s;};
      wrap.appendChild(b);
    });
    els.chatLog.appendChild(wrap);
    scrollChat();
  }
  function showTyping(){
    const el=document.createElement('div');
    el.id='jv-typing'; el.className='jv-bubble jv-bubble-assistant jv-typing';
    el.innerHTML='<div class=\"jv-bubble-avatar\"><i class=\"fa-solid fa-robot\"></i></div><div class=\"jv-bubble-body\"><div class=\"jv-bubble-name\">Jarvis</div><div class=\"jv-typing-dots\"><span></span><span></span><span></span></div></div>';
    els.chatLog.appendChild(el); scrollChat();
  }
  function hideTyping(){ const e=document.getElementById('jv-typing'); if(e) e.remove(); }
  function scrollChat(){ els.chatLog.scrollTop=els.chatLog.scrollHeight; }
  function escHtml(s){ const d=document.createElement('div'); d.textContent=s; return d.innerHTML; }
  function esc(s){ return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;'); }

  // ---------- Actions (Command Center) ----------
  function doAnalyze(){
    if(!state.projectId) return addBubble('Select a project first.','assistant');
    addBubble('Analyzing project...','user');
    showTyping(); setTask('Analyzing...');
    fetch(API+'/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id: state.projectId})})
      .then(handleJson).then(d=>{
        hideTyping(); setTask('Idle');
        if(!d.success) { renderIssues([]); return addBubble('Analyze failed: '+(d.error||''),'assistant'); }
        const html = '<strong>Framework:</strong> '+esc(d.framework||'')+'<br><strong>Files:</strong> '+(d.file_count||0)+
          '<br><strong>Issues:</strong> '+(d.issues||[]).map(i=>'<div class=\"'+(i.type==='error'?'issue-error':'issue-warning')+'\">• '+esc(i.message)+' '+(i.file?'('+esc(i.file)+')':'')+'</div>').join('')+
          '<br><strong>Suggestions:</strong><ul><li>'+(d.suggestions||[]).map(esc).join('</li><li>')+'</li></ul>';
        addBubble('Analysis complete','assistant');
        if(els.analysisCard){ els.analysisCard.style.display='block'; els.analysisContent.innerHTML=html; }
        renderIssues(d.issues||[]);
        // Also update project intelligence recent
        addRecentChange('Analysis', 'Project analyzed');
        updateTopBar();
      }).catch(e=>{ hideTyping(); setTask('Idle'); renderIssues([]); addBubble('Error: '+e.message,'assistant'); });
  }
  function doFix(){
    const err = prompt('Describe error or paste log (e.g. Gemini 429 quota, preview blank):');
    if(!err) return;
    showTyping(); setTask('Fixing errors...');
    fetch(API+'/fix',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id: state.projectId, error: err})})
      .then(handleJson).then(d=>{
        hideTyping(); setTask('Idle');
        if(!d.success) return addBubble('Fix failed: '+(d.error||''),'assistant');
        let msg = '**Problem:** '+d.problem+'\n**Cause:** '+d.cause+'\n**Solution:** '+d.solution+'\n\n'+(d.explanation||'');
        if(d.fixed_files && Object.keys(d.fixed_files).length) msg += '\n\nFixed files: '+Object.keys(d.fixed_files).join(', ');
        addBubble(msg,'assistant');
        if(d.fixed_files && Object.keys(d.fixed_files).length){
          showApproval({files_changed: Object.keys(d.fixed_files), fixed_files: d.fixed_files, explanation: d.explanation||d.solution, reason: d.cause});
          Object.keys(d.fixed_files).forEach(f=> addRecentChange(f, 'Fix: '+d.problem));
          renderIssues([]); // clear after fix
        }
        if(d.solution && d.solution.includes('Switch provider')){
          addBubble('Tip: Use the AI Model selector in workspace to switch to Groq Llama.','assistant');
        }
      }).catch(e=>{ hideTyping(); setTask('Idle'); addBubble('Error: '+e.message,'assistant'); });
  }
  function doExplain(){
    const fp = prompt('Enter file path to explain (e.g. index.html) or leave empty to paste code:');
    if(fp===null) return;
    let code=null;
    if(!fp){
      code = prompt('Paste code:');
      if(!code) return;
    }
    showTyping();
    fetch(API+'/explain',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id: state.projectId, file_path: fp||null, code})})
      .then(handleJson).then(d=>{
        hideTyping();
        if(!d.success) return addBubble('Explain failed: '+(d.error||''),'assistant');
        addBubble(d.explanation || 'No explanation','assistant');
      }).catch(e=>{ hideTyping(); addBubble('Error: '+e.message,'assistant'); });
  }
  function showModify(show){
    const m=document.getElementById('jvModifyModal');
    if(m) m.style.display = show ? 'flex' : 'none';
  }
  function submitModify(){
    const inp=document.getElementById('jvModifyInput');
    const req=(inp && inp.value||'').trim();
    if(!req) return;
    if(!state.projectId) return addBubble('Select a project first.','assistant');
    showModify(false);
    addBubble(req,'user'); setTask('Modifying...');
    showTyping();
    fetch(API+'/modify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id: state.projectId, request: req})})
      .then(handleJson).then(d=>{
        hideTyping(); setTask('Idle');
        if(!d.success) return addBubble('Modify failed: '+(d.error||d.explanation||''),'assistant');
        // Approval workflow - show before final apply
        handleModifyResponse(d);
        if(inp) inp.value='';
      }).catch(e=>{ hideTyping(); setTask('Idle'); addBubble('Error: '+e.message,'assistant'); });
  }
  function doRunTest(){
    addBubble('Running quick test...','user');
    // Simple test: call analyze and check health
    fetch(API+'/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id: state.projectId||''})})
      .then(handleJson).then(d=>{
        const ok = d.file_count>0 && (!d.issues || d.issues.filter(i=>i.type==='error').length===0);
        addBubble(ok ? '✓ Test passed: project looks healthy' : 'Test found issues - see analysis','assistant');
        if(d.issues) d.issues.forEach(i=> addBubble((i.type==='error'?'✗ ':'⚠ ')+i.message,'assistant'));
      }).catch(e=> addBubble('Test error: '+e.message,'assistant'));
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
