'use strict';
let state=null,csrf='',view='Datos abiertos';
const $=id=>document.getElementById(id);
const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(route,data){const r=await fetch('/api/'+route,{method:data?'POST':'GET',headers:data?{'Content-Type':'application/json','X-CSRF-Token':csrf}:{},body:data?JSON.stringify(data):undefined});const b=await r.json();if(!r.ok)throw Error(b.error||'No se pudo completar la operación');return b;}
async function apiGet(route,params={}){const r=await fetch('/api/'+route+'?'+new URLSearchParams(params));const b=await r.json();if(!r.ok)throw Error(b.error||'No se pudo consultar la fuente oficial');return b;}
function message(s){$('notice').textContent=s;}
function field(name,label,type='text'){return `<label>${label}<input name="${name}" type="${type}" required ${type==='datetime-local'?'step="1"':''}></label>`;}
function options(name,label,items,key,labelKey){return `<label>${label}<select name="${name}" required><option value="">Selecciona</option>${items.map(x=>`<option value="${escape(x[key])}">${escape(x[labelKey])}</option>`).join('')}</select></label>`;}
function form(action,content,label='Guardar'){return `<form data-action="${action}">${content}<button>${label}</button></form>`;}
function table(rows,cols){return `<div class="table"><table><thead><tr>${cols.map(c=>`<th>${escape(c[1])}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${cols.map(c=>`<td>${escape(r[c[0]]??'—')}</td>`).join('')}</tr>`).join('')||`<tr><td colspan="${cols.length}">Sin registros para los filtros aplicados.</td></tr>`}</tbody></table></div>`;}
const realColumns={
  consumos:[['fuente_id','Fuente'],['prestador','Prestador'],['municipio','Municipio'],['periodo','Período'],['estrato_uso','Estrato/uso'],['suscriptores','Suscriptores'],['consumo_basico_m3','Consumo básico m³'],['consumo_complementario_m3','Complementario y suntuario m³'],['consumo_total_m3','Total publicado m³'],['calidad_alerta','Alerta de calidad']],
  interrupciones:[['fuente_id','Fuente'],['municipio','Municipio'],['inicio','Inicio'],['fin','Fin'],['duracion_horas','Horas'],['motivo','Motivo'],['impacto','Impacto'],['circuito','Circuito']],
  cobertura:[['fuente_id','Fuente'],['municipio','Municipio'],['comuna','Comuna'],['periodo','Período'],['estrato_uso','Estrato/uso'],['suscriptores','Suscriptores'],['cobertura_pct','Cobertura %'],['calidad_alerta','Alerta de calidad']],
  prestadores:[['fuente_id','Fuente'],['nombre','Prestador'],['servicio','Servicio'],['municipio_prestacion','Municipio de prestación'],['municipio_domicilio','Municipio de domicilio']]
};
async function loadRealForm(form){const type=form.dataset.real;const target=$('real-'+type);target.innerHTML='<p>Consultando…</p>';try{const params=Object.fromEntries(new FormData(form));params.limite='50';const result=await apiGet('real/'+type,params);target.innerHTML=`<p><strong>${result.total}</strong> registros oficiales encontrados. Se muestran hasta 50 por consulta.</p>`+table(result.filas,realColumns[type]);}catch(e){target.innerHTML=`<p class="warning">${escape(e.message)}</p>`;}}
async function loadReal(){try{const result=await apiGet('real/resumen');const c=result.conteos;$('real-summary').innerHTML=`<div class="stats">${[[c.consumos,'Consumos agregados'],[c.interrupciones,'Interrupciones oficiales'],[c.cobertura,'Registros de cobertura'],[c.prestadores,'Prestadores de referencia']].map(([n,t])=>`<div class="stat"><strong>${escape(n)}</strong><span>${t}</span></div>`).join('')}</div><h3>Fuentes importadas</h3>${table(result.fuentes,[['nombre','Dataset'],['entidad','Entidad'],['granularidad','Granularidad'],['fecha_actualizacion','Actualización']])}<p class="muted">No se suman consumos de períodos, prestadores o metodologías incompatibles. Use los filtros para consultar cada registro con su fuente y período.</p>`;for(const form of document.querySelectorAll('[data-real]')){form.onsubmit=e=>{e.preventDefault();loadRealForm(form);};loadRealForm(form);}}catch(e){$('real-summary').innerHTML=`<p class="warning">${escape(e.message)}</p>`;}}
async function refresh(){state=await api('state');csrf=state.csrf;$('login').hidden=true;$('workspace').hidden=false;$('logout').hidden=false;$('account').textContent=state.cuenta.login+' · '+state.cuenta.aq;render();}
function render(){const write=state.cuenta.rol!=='consulta';const admin=state.cuenta.rol==='admin';const tabs=['Datos abiertos','Resumen simulado','Usuarios simulados','Lecturas simuladas','Novedades simuladas','Reportes simulados','Auditoría simulada',...(admin?['Permisos']:[])];$('nav').innerHTML=tabs.map(t=>`<button data-view="${t}" class="${view===t?'active':''}">${t}</button>`).join('');$('title').textContent=view;let s='';
if(view==='Resumen simulado'){s=`<div class="stats">${[[state.usuario.length,'Usuarios sintéticos'],[state.medidor.length,'Medidores sintéticos'],[state.total_consumo+' m³','Consumo sintético'],[state.novedad.filter(n=>n.estado!=='cerrada').length,'Novedades sintéticas abiertas']].map(([n,t])=>`<div class="stat"><strong>${escape(n)}</strong><span>${t}</span></div>`).join('')}</div><h2>Entorno B · Práctica simulada</h2><p>Los registros pertenecen a <strong>${escape(state.cuenta.aq)}</strong>. Los roles se verifican en el servidor y cada operación conserva auditoría.</p><p class="warning">Escenario de práctica simulada. No representa un prestador real ni mide ahorro de agua, sequía o calidad del servicio.</p><h3>Últimas lecturas sintéticas</h3>${table(state.lectura.slice(-8).reverse(),[['usuario','Usuario'],['serial','Medidor'],['fecha','Instante'],['valor','Lectura m³'],['consumo','Consumo m³'],['estado','Estado']])}`;}
if(view==='Datos abiertos'){s=`
<h2>Entorno A · Datos abiertos reales de Antioquia</h2>
<p>Los registros de esta sección proceden de fuentes oficiales. Las cifras de suscriptores y consumos conservan su nivel agregado: no representan personas, medidores ni lecturas individuales.</p>
<div id="real-summary"><p>Cargando inventario oficial…</p></div>
<h3>Consumos reportados</h3>
<form data-real="consumos"><label>Prestador<input name="prestador"></label><label>Municipio<input name="municipio"></label><label>Desde<input name="desde" type="date"></label><label>Hasta<input name="hasta" type="date"></label><button>Consultar</button></form><div id="real-consumos"></div>
<h3>Interrupciones oficiales</h3>
<form data-real="interrupciones"><label>Municipio<input name="municipio"></label><label>Motivo<input name="motivo"></label><label>Desde<input name="desde" type="date"></label><label>Hasta<input name="hasta" type="date"></label><button>Consultar</button></form><div id="real-interrupciones"></div>
<h3>Cobertura reportada</h3>
<form data-real="cobertura"><label>Comuna<input name="comuna"></label><label>Estrato o uso<input name="estrato"></label><button>Consultar</button></form><div id="real-cobertura"></div>
<h3>Directorio oficial de prestadores</h3>
<form data-real="prestadores"><label>Municipio<input name="municipio"></label><label>Prestador<input name="prestador"></label><button>Consultar</button></form><div id="real-prestadores"></div>
<h2>Contexto documental de La Acuarela</h2>
<p>El diagnóstico institucional aporta contexto del sistema real, separado de los registros operativos sintéticos del Entorno B.</p>
<h3>Caracterización general e infraestructura</h3>
<p>El informe ubica el sistema en el corregimiento de San Cristóbal, Medellín, y reporta 3.746 suscriptores para 2019. Describe tres captaciones, líneas de aducción, dos desarenadores, tres plantas de tratamiento, tanques de almacenamiento y 48,35 km de redes de distribución. También registra macromedición en salidas de tanques y una cobertura de micromedición del 100 % informada por el operador; el documento no publica históricos individuales de lecturas.</p>
<p class="muted"><strong>Fuente:</strong> Alcaldía de Medellín y Universidad de Antioquia (2021), <em>Diagnóstico PSAAA</em>, pp. 545-558 del informe (pp. 751-764 del archivo PDF).</p>
<h3>Concesiones de agua</h3>
${table([
  {fuente:'Quebrada La Francisca',caudal:'14,18 l/s',resolucion:'160AN-RES1706-2781',vigencia:'2 jun. 2017 - 2 jun. 2027'},
  {fuente:'Quebrada La Palma',caudal:'15,0 l/s',resolucion:'130AN-9003',vigencia:'4 may. 2009 - 4 may. 2019'},
  {fuente:'Quebrada La Legía',caudal:'2,96 l/s',resolucion:'160AN-RES1810-5825',vigencia:'25 oct. 2018 - 25 oct. 2028'}
],[['fuente','Fuente'],['caudal','Caudal concesionado'],['resolucion','Resolución'],['vigencia','Vigencia reportada']])}
<p class="muted"><strong>Fuente:</strong> Tabla 308, p. 546 del informe (p. 752 del archivo PDF). La Tabla 308 reporta 14,18 l/s para La Francisca; la Tabla 313 usa 14,17 l/s al calcular el total concesionado. Se conservan ambos valores tal como aparecen en la fuente.</p>
<h3>Índice de calidad del agua en la fuente (ICA)</h3>
${table([
  {punto:'Acuarela',anio:'2016',ica:'17,5',clasificacion:'Buena'},
  {punto:'Acuarela',anio:'2017',ica:'17,78',clasificacion:'Buena'},
  {punto:'Entrada PTAP La Acuarela',anio:'2019',ica:'21,5',clasificacion:'Aceptable'},
  {punto:'Bocatoma La Palma',anio:'2019',ica:'15',clasificacion:'Buena'},
  {punto:'Bocatoma La Francisca',anio:'2019',ica:'30,5',clasificacion:'Aceptable'}
],[['punto','Punto de muestreo'],['anio','Año'],['ica','ICA'],['clasificacion','Clasificación']])}
<p class="muted"><strong>Fuente:</strong> Tabla 309, pp. 546-547 del informe (pp. 752-753 del archivo PDF). El ICA caracteriza la fuente y no corresponde a lecturas de consumo ni a micromedición.</p>
<h3>Puntos de muestreo e IRCA</h3>
${table([{total:'16',sin_concertar:'4',concertados:'12',materializados:'8',urbanos:'6',rurales:'9'}],[['total','Total'],['sin_concertar','Sin concertar'],['concertados','Concertados'],['materializados','Materializados'],['urbanos','Urbanos'],['rurales','Rurales']])}
<p class="muted"><strong>Fuente:</strong> Tabla 310, p. 554 del informe (p. 760 del archivo PDF). La fuente reporta 16 puntos totales, pero la suma de urbanos y rurales mostrada en la tabla es 15; no se corrige ni se completa el dato.</p>
${table([
  {anio:'2016',irca:'2,64',riesgo:'Sin riesgo'},
  {anio:'2017',irca:'0,00',riesgo:'Sin riesgo'},
  {anio:'2018',irca:'0,00',riesgo:'Sin riesgo'},
  {anio:'2019',irca:'0,68',riesgo:'Sin riesgo'}
],[['anio','Año'],['irca','IRCA promedio'],['riesgo','Valoración']])}
<p class="muted"><strong>Fuente:</strong> Tabla 311, p. 555 del informe (p. 761 del archivo PDF), a partir de reportes SIVICAP según el documento. Estos valores no son resultados producidos por aguaANTIOQUIA.</p>
<h3>Capacidad documentada del sistema</h3>
${table([
  {indicador:'Caudal concesionado',valor:'32,13 l/s'},
  {indicador:'Caudal de diseño de las PTAP',valor:'47,8 l/s'},
  {indicador:'Caudal de operación de las PTAP',valor:'33,4 l/s'},
  {indicador:'Suscriptores en 2019',valor:'3.746'},
  {indicador:'Población calculada según caudal concesionado',valor:'13.566 habitantes'},
  {indicador:'Población calculada según caudal de diseño',valor:'19.855 habitantes'},
  {indicador:'Almacenamiento existente',valor:'1.208 m³'},
  {indicador:'Almacenamiento requerido según caudal de diseño',valor:'1.377 m³'}
],[['indicador','Indicador documental'],['valor','Valor reportado']])}
<p class="muted"><strong>Fuente:</strong> Tablas 313 y 314, pp. 559-560 del informe (pp. 765-766 del archivo PDF). Son cálculos y condiciones documentadas por la fuente; no son mediciones del prototipo ni amplían su alcance funcional.</p>
<h3>Referencia</h3>
<p>Alcaldía de Medellín &amp; Universidad de Antioquia. (2021). <em>Diagnóstico del Plan Sectorial de Acueducto, Alcantarillado y Aseo de Medellín 2020-2023</em>. Contrato interadministrativo 4600085938 de 2020.</p>`;}
if(view==='Usuarios simulados'){s='<h2>Entorno B · Usuarios sintéticos</h2>'+table(state.usuario,[['id','ID'],['codigo','Código'],['activo','Activo']]);if(write)s+=form('usuario',field('codigo','Código de usuario sintético'));if(admin){
  s+='<h3>Actualizar usuario</h3>'+form('actualizar_usuario',
    options('id','Usuario',state.usuario,'id','codigo')+
    field('codigo','Código actualizado')+
    '<label>Estado<select name="activo" required><option value="">Selecciona</option>'+
    '<option value="true">Activo</option><option value="false">Inactivo</option></select></label>'+
    field('motivo','Motivo del cambio'),
    'Actualizar usuario');
}
s+='<h2>Predios</h2>'+table(state.predio,[['id','ID'],['codigo','Código'],['usuario','Usuario ID']]);if(write)s+=form('predio',field('codigo','Código de predio')+options('usuario','Usuario',state.usuario.filter(u=>u.activo),'id','codigo'));s+='<h2>Medidores</h2>'+table(state.medidor,[['id','ID'],['serial','Serial']]);if(write)s+=form('medidor',field('serial','Serial'));s+='<h2>Instalaciones y vigencias</h2>'+table(state.instalacion,[['id','ID'],['predio','Predio ID'],['medidor','Medidor ID'],['inicio','Inicio'],['fin','Fin']]);if(write){s+=form('instalacion',options('predio','Predio',state.predio,'id','codigo')+options('medidor','Medidor',state.medidor,'id','serial')+field('inicio','Inicio','datetime-local'));s+='<h3>Cerrar instalación antes de reemplazar medidor</h3>'+form('cerrar_instalacion',options('id','Instalación',state.instalacion.filter(i=>!i.fin),'id','id')+field('fin','Fin','datetime-local')+field('motivo','Motivo'),'Cerrar instalación');}}
if(view==='Lecturas simuladas'){s='<h2>Entorno B · Lecturas sintéticas</h2><p class="muted">Una primera lectura establece línea base. Las decrecientes quedan pendientes y no generan consumo. Estas lecturas no proceden de fuentes oficiales.</p>'+table(state.lectura,[['id','ID'],['usuario','Usuario'],['serial','Medidor'],['fecha','Fecha'],['valor','Lectura m³'],['desde','Desde'],['consumo','Consumo m³'],['estado','Estado']]);if(write){s+=form('lectura',options('instalacion','Instalación',state.instalacion,'id','id')+field('fecha','Fecha','datetime-local')+field('valor','Lectura acumulada m³'));s+='<h3>Resolver o corregir con auditoría</h3>'+form('corregir_lectura',options('id','Lectura',state.lectura,'id','id')+field('valor','Valor corregido m³')+'<label>Estado<select name="estado"><option value="valida">Válida</option><option value="descartada">Descartada</option></select></label>'+field('motivo','Motivo de corrección'));}}
if(view==='Novedades simuladas'){s='<h2>Entorno B · Novedades sintéticas</h2>'+table(state.novedad,[['id','ID'],['descripcion','Descripción'],['estado','Estado'],['apertura','Apertura'],['cierre','Cierre'],['motivo','Motivo']]);if(write){s+=form('novedad',field('descripcion','Descripción sintética (mínimo 10 caracteres)'));s+=form('estado_novedad',options('id','Novedad',state.novedad.filter(n=>n.estado!=='cerrada'),'id','id')+'<label>Próximo estado<select name="estado"><option value="en gestion">En gestión</option><option value="cerrada">Cerrada</option></select></label>'+field('motivo','Motivo'));}}
if(view==='Reportes simulados'){s='<h2>Entorno B · Reporte de consumos sintéticos</h2><form id="filters"><label>Usuario<select name="usuario"><option value="">Todos</option>'+state.usuario.map(u=>`<option>${escape(u.codigo)}</option>`).join('')+'</select></label><label>Mes de la lectura final<input name="mes" type="month"></label><button>Aplicar filtros</button></form><div id="report"></div><p id="export"></p>';}
if(view==='Auditoría simulada'){s='<h2>Entorno B · Historial de operaciones sintéticas</h2><p>Sin edición o borrado desde la aplicación. Cada corrección conserva los valores anteriores.</p>'+state.auditoria.slice().reverse().map(a=>`<details><summary>#${a.id} · ${escape(a.instante)} · ${escape(a.accion)} · actor ${a.actor}</summary><pre>${escape(JSON.stringify(a,null,2))}</pre></details>`).join('');}
if(view==='Permisos'){s='<h2>Administración del mismo acueducto</h2>'+table(state.cuentas,[['id','ID'],['login','Cuenta'],['rol','Rol'],['exportar','Puede exportar']])+form('permisos',options('id','Cuenta',state.cuentas,'id','login')+'<label>Rol<select name="rol"><option value="consulta">Consulta</option><option value="operador">Operador</option><option value="admin">Administrador</option></select></label><label>Exportación<select name="exportar"><option value="false">Denegada</option><option value="true">Permitida</option></select></label>'+field('motivo','Motivo de cambio'));}
$('workspace').innerHTML=s;
if(view==='Datos abiertos')loadReal();
const userForm=$('workspace').querySelector('[data-action="actualizar_usuario"]');
if(userForm){
  userForm.elements.id.onchange=()=>{
    const user=state.usuario.find(u=>String(u.id)===userForm.elements.id.value);
    userForm.elements.codigo.value=user?.codigo??'';
    userForm.elements.activo.value=user?String(Boolean(user.activo)):'';
  };
}
if(view==='Reportes simulados'){function report(){const d=Object.fromEntries(new FormData($('filters')));const rows=state.lectura.filter(r=>(!d.usuario||r.usuario===d.usuario)&&(!d.mes||r.fecha.startsWith(d.mes)));const total=rows.reduce((n,r)=>n+(r.consumo===null?0:Math.round(Number(r.consumo)*1000)),0);$('report').innerHTML=`<p><strong>Total del filtro: ${(total/1000).toFixed(3)} m³</strong> · ${rows.length} lecturas sintéticas</p>`+table(rows,[['usuario','Usuario'],['serial','Medidor'],['desde','Desde'],['fecha','Hasta'],['valor','Lectura m³'],['consumo','Consumo m³'],['estado','Estado']]);$('export').innerHTML=state.cuenta.exportar?`<a href="/api/export?${new URLSearchParams(d)}">Descargar CSV sintético</a>`:'Tu cuenta no tiene permiso de exportación.';}$('filters').onsubmit=e=>{e.preventDefault();report();};report();}}
$('nav').onclick=e=>{const t=e.target.closest('[data-view]');if(t){view=t.dataset.view;message('');render();}};
$('login-form').onsubmit=async e=>{e.preventDefault();try{const b=await api('login',Object.fromEntries(new FormData(e.target)));csrf=b.csrf;e.target.reset();await refresh();message('Sesión iniciada');}catch(x){message(x.message);}};
$('logout').onclick=async()=>{try{await api('logout',{});state=null;csrf='';$('workspace').hidden=true;$('login').hidden=false;$('logout').hidden=true;$('account').textContent='';$('nav').textContent='';$('title').textContent='Bienvenido';message('Sesión cerrada');}catch(x){message(x.message);}};
$('workspace').onsubmit=async e=>{const f=e.target;if(!f.dataset.action)return;e.preventDefault();try{const d=Object.fromEntries(new FormData(f));for(const key of ['fecha','inicio','fin'])if(d[key])d[key]=new Date(d[key]).toISOString();for(const key of ['id','usuario','predio','medidor','instalacion'])if(d[key])d[key]=Number(d[key]);if('exportar'in d)d.exportar=d.exportar==='true';if('activo'in d)d.activo=d.activo==='true';const b=await api(f.dataset.action,d);await refresh();message(b.estado==='pendiente'?'Lectura pendiente de revisión: no genera consumo.':'Operación registrada con auditoría.');}catch(x){message(x.message);}};
refresh().catch(()=>{});
