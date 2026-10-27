(() => {
  const app = document.getElementById('live-app') || document.getElementById('live-host-app');
  if (!app) return;
  const host = app.id === 'live-host-app';
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
  let room = null, selectedKind = 'chat', stateTimer = null, interactionCache = [];
  const $ = id => document.getElementById(id);
  const inviteField = $('invite-participant-id');
  if(inviteField){inviteField.type='text';inviteField.removeAttribute('min');inviteField.maxLength=30;inviteField.placeholder='Attendee registration ID';}
  if(inviteField?.parentElement?.nextElementSibling)inviteField.parentElement.nextElementSibling.textContent='Invitation grants publishing permission for 30 minutes. Enter a registration ID for this event.';
  const api = async (url, body = {}) => {
    const response = await fetch(url, {method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:JSON.stringify(body)});
    const data = await response.json(); if (!response.ok || data.ok === false) throw new Error(data.message || 'Request failed.'); return data;
  };
  const addVideo = (track, participant) => {
    if (track.kind === 'audio') {
      const audio=track.attach();audio.autoplay=true;audio.dataset.identity=participant.identity;$('media-stage').appendChild(audio);return;
    }
    if (track.kind !== 'video') return;
    const stage = $('media-stage'); $('stage-placeholder')?.remove();
    const el = track.attach(); el.className = 'live-video'; el.dataset.identity = participant.identity; stage.appendChild(el);
  };
  async function connect() {
    if (room) return;
    const result = await api(app.dataset.tokenUrl);
    const Room = window.LivekitClient?.Room;
    if (!Room) throw new Error('LiveKit client failed to load.');
    room = new Room({adaptiveStream:true,dynacast:true});
    room.on(window.LivekitClient.RoomEvent.TrackSubscribed, (track, publication, participant) => addVideo(track, participant));
    room.on(window.LivekitClient.RoomEvent.TrackUnsubscribed, track => track.detach().forEach(node => node.remove()));
    room.on(window.LivekitClient.RoomEvent.Disconnected, () => { $('connection-status').textContent='Disconnected'; });
    room.on(window.LivekitClient.RoomEvent.DataReceived, payload => {
      try { const message=JSON.parse(new TextDecoder().decode(payload));
        if(message.type==='interaction'){if(!interactionCache.some(item=>item.id===message.id))interactionCache.push(message);appendInteraction(message);renderPolls();}
        if(message.type==='lifecycle'){ $('meeting-status').textContent=message.status; if(message.status==='ended'&&room)room.disconnect(); }
        if(message.type==='speaker_invited'&&String(message.participant_id)===app.dataset.participantId){$('join-stage').hidden=false;}
        if(message.type==='interaction_moderated'){const item=interactionCache.find(entry=>entry.id===message.id);if(item)item.status=message.status;const node=document.querySelector(`[data-interaction-id="${message.id}"]`);if(node&&message.status==='hidden')node.remove();else if(node)node.dataset.status=message.status;renderPolls();}
      } catch (_) {}
    });
    await room.connect(result.server_url, result.token);
    $('meeting-status').textContent = 'Connected · ' + result.role;
    if (result.role === 'host' || result.role === 'speaker') {
      if(result.role==='host'||result.role==='speaker'){
        const camera=await room.localParticipant.setCameraEnabled(true);
        await room.localParticipant.setMicrophoneEnabled(true);
        if(camera?.track){$('stage-placeholder')?.remove();const video=camera.track.attach();video.className='live-video';$('media-stage').appendChild(video);}
      }
      $('connection-status').textContent='Publishing audio/video';
    } else {
      $('connection-status').textContent='Viewer mode · receive-only';
    }
  }
  async function refresh() {
    const response=await fetch(app.dataset.stateUrl); if(!response.ok) return;
    const state=await response.json(); $('meeting-status').textContent=state.status; interactionCache=state.interactions;
    const box=$('interaction-list');
    if(box){ box.replaceChildren(); state.interactions.filter(item=>item.status!=='hidden').forEach(item=>{
      const row=document.createElement('div'); row.className='border-bottom py-2'; row.dataset.interactionId=item.id; row.dataset.status=item.status;
      const title=document.createElement('strong'); title.textContent=`${item.name} · ${item.kind}`;
      const body=document.createElement('div'); body.textContent=item.body || (item.kind==='hand'?'Raised hand':'');
      row.append(title,body);
      if(host && item.kind==='question') ['answer','hide','close'].forEach(action=>{const button=document.createElement('button');button.className='btn btn-sm btn-outline-secondary me-1 mt-1';button.textContent=action;button.onclick=()=>api(app.dataset.stateUrl.replace('/state',`/moderate/${item.id}`),{action}).then(refresh).catch(showError);row.append(button);});
      if(host && item.kind==='chat'){const hide=document.createElement('button');hide.className='btn btn-sm btn-outline-secondary mt-1';hide.textContent='Hide';hide.onclick=()=>api(app.dataset.stateUrl.replace('/state',`/moderate/${item.id}`),{action:'hide'}).then(refresh).catch(showError);row.append(hide);}
      box.append(row);
    }); }
    renderPolls();
    if(host) renderSpeakers(state.speakers);
  }
  function renderSpeakers(speakers){
    let list=$('speaker-list');if(!list){list=document.createElement('div');list.id='speaker-list';$('host-message')?.after(list);}list.replaceChildren();
    if(!speakers.length){list.textContent='No invited speakers.';return;}
    speakers.forEach(s=>{const line=document.createElement('div');line.className='d-flex justify-content-between align-items-center border-bottom py-2';const name=document.createElement('span');name.textContent=`${s.name} · ${s.status}`;line.append(name);
      if(s.status==='accepted')[['Mute',`speaker/${s.participant_id}/mute`],['Remove',`speaker/${s.participant_id}/remove`]].forEach(([label,path])=>{const b=document.createElement('button');b.className='btn btn-sm btn-outline-danger ms-1';b.textContent=label;b.onclick=()=>api(`/events/${app.dataset.eventId}/live/${path}`).then(refresh).catch(showError);line.append(b);});list.append(line);});
  }
  function showError(error){const target=$('host-message')||$('connection-status');if(target)target.textContent=error.message;}
  function appendInteraction(item) {
    const box=$('interaction-list'); if(!box)return;
    if(document.querySelector(`[data-interaction-id="${item.id}"]`))return;
    const row=document.createElement('div'); row.className='border-bottom py-2'; row.dataset.interactionId=item.id; row.dataset.status=item.status||'open';
    const title=document.createElement('strong'); title.textContent=`${item.name} · ${item.kind}`;
    const body=document.createElement('div'); body.textContent=item.body || (item.kind==='hand'?'Raised hand':''); row.append(title,body);
    if(host && item.kind==='question') ['answer','hide','close'].forEach(action=>{const button=document.createElement('button');button.className='btn btn-sm btn-outline-secondary me-1 mt-1';button.textContent=action;button.onclick=()=>api(app.dataset.stateUrl.replace('/state',`/moderate/${item.id}`),{action}).then(refresh).catch(showError);row.append(button);});
    if(host && item.kind==='chat'){const hide=document.createElement('button');hide.className='btn btn-sm btn-outline-secondary mt-1';hide.textContent='Hide';hide.onclick=()=>api(app.dataset.stateUrl.replace('/state',`/moderate/${item.id}`),{action:'hide'}).then(refresh).catch(showError);row.append(hide);}
    if(item.kind==='poll') (item.metadata.options||[]).forEach(option=>{const button=document.createElement('button');button.className='btn btn-sm btn-outline-primary me-1 mt-1';button.textContent=option;button.onclick=()=>api(app.dataset.interactionUrl,{kind:'poll_vote',body:'',metadata:{poll_id:item.id,option}}).catch(showError);row.append(button);});
    box.append(row); box.scrollTop=box.scrollHeight;
  }
  function renderPolls(){
    const panel=$('poll-list');if(!panel)return;panel.replaceChildren();
    const polls=interactionCache.filter(item=>item.kind==='poll'&&item.status==='open');
    if(!polls.length){panel.textContent='No active polls.';return;}
    polls.forEach(poll=>{const question=document.createElement('p');question.className='fw-semibold';question.textContent=poll.body;panel.append(question);
      const votes=interactionCache.filter(item=>item.kind==='poll_vote'&&Number(item.metadata.poll_id)===Number(poll.id));
      (poll.metadata.options||[]).forEach(option=>{const count=votes.filter(vote=>vote.metadata.option===option).length;const button=document.createElement('button');button.className='btn btn-sm btn-outline-primary me-1 mb-1';button.textContent=`${option} (${count})`;button.onclick=()=>api(app.dataset.interactionUrl,{kind:'poll_vote',body:'',metadata:{poll_id:poll.id,option}}).catch(showError);panel.append(button);});
    });
  }
  $('join-live')?.addEventListener('click',()=>connect().catch(showError));
  $('join-stage')?.addEventListener('click',async()=>{try{if(room){await room.disconnect();room=null;}await connect();}catch(error){showError(error);}});
  $('leave-live')?.addEventListener('click',async()=>{if(room){await room.disconnect();room=null;}});
  $('start-live')?.addEventListener('click',()=>api(app.dataset.startUrl).then(refresh).catch(showError));
  $('end-live')?.addEventListener('click',()=>{if(confirm('End this live event for everyone?'))api(app.dataset.endUrl).then(()=>{if(room)room.disconnect();refresh();}).catch(showError);});
  $('invite-speaker')?.addEventListener('click',()=>api(app.dataset.inviteUrl,{registration_id:$('invite-participant-id').value}).then(data=>{$('host-message').textContent=`Invited ${data.name}.`;refresh();}).catch(showError));
  $('interaction-form')?.addEventListener('submit',event=>{event.preventDefault();const input=$('interaction-input');api(app.dataset.interactionUrl,{kind:selectedKind,body:input.value}).then(()=>{input.value='';refresh();}).catch(showError);});
  document.querySelectorAll('[data-kind-tab]').forEach(button=>button.addEventListener('click',()=>{selectedKind=button.dataset.kindTab;document.querySelectorAll('[data-kind-tab]').forEach(item=>item.classList.toggle('active',item===button));$('interaction-input').placeholder=selectedKind==='chat'?'Write a message…':'Ask a question…';}));
  $('raise-hand')?.addEventListener('click',()=>api(app.dataset.interactionUrl,{kind:'hand',body:''}).then(refresh).catch(showError));
  $('create-poll')?.addEventListener('click',()=>{const options=$('poll-options').value.split(',').map(x=>x.trim()).filter(Boolean).slice(0,8);if(options.length<2){showError(new Error('Enter at least two comma-separated options.'));return;}api(app.dataset.interactionUrl,{kind:'poll',body:$('poll-question').value,metadata:{options}}).then(refresh).catch(showError);});
  refresh(); if(host)stateTimer=setInterval(refresh,5000); window.addEventListener('beforeunload',()=>{clearInterval(stateTimer);if(room)room.disconnect();});
})();
