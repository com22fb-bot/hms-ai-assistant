"""Auditoría fase 1: 18 escenarios contra el motor de producción (safe_case_classifier + case_engine).
Solo lectura: cliente Supabase FALSO en memoria, datos sintéticos, sin red."""
import json, sys
from app.services import safe_case_classifier as scc, case_engine as ce
from app.services.mail_direction import account_identity, resolve_ownership, normalize_address

class Q:
    def __init__(s, rows): s.rows=list(rows)
    def select(s,*a,**k): return s
    def eq(s,col,val):
        if col.startswith("metadata->>"):
            k=col.split(">>")[1]; s.rows=[r for r in s.rows if (r.get("metadata") or {}).get(k)==val]
        else: s.rows=[r for r in s.rows if r.get(col)==val]
        return s
    def in_(s,col,vals): s.rows=[r for r in s.rows if r.get(col) in vals]; return s
    def gte(s,col,val): s.rows=[r for r in s.rows if str(r.get(col,""))>=val]; return s
    def order(s,*a,**k): return s
    def limit(s,n): s.rows=s.rows[:n]; return s
    def execute(s):
        class R: pass
        r=R(); r.data=s.rows; return r
class FakeClient:
    def __init__(s, tables): s.t=tables
    def table(s,n): return Q(s.t.get(n,[]))

YAHOO={"id":"acc-y","email":"propia-1@yahoo.example","identity_aliases":[]}
GMAIL={"id":"acc-g","email":"propia2@gmail.com","identity_aliases":[]}
def M(sender,subject,body,labels=("INBOX",),**kw):
    d={"sender":sender,"subject":subject,"body_text":body,"labels":list(labels),"recipients":kw.pop("to",["propia-1@yahoo.example"]),"is_unread":True}
    d.update(kw); return d
def classify(m, acc=YAHOO, existing=None):
    own=resolve_ownership(m, account_identity(acc))
    r=scc.classify_message(m, existing_case=existing, ownership=own)
    return {"ownership":own["ownership"],"clase":r[0],"score":r[1],"motivo":r[2],"crea_o_actualiza_caso":r[3]}
def find(cases, subj, thread=None, event_key=None, own=False, reply_ids=None, msgs=None, links=None):
    c=FakeClient({"intelligent_cases":cases,"communication_messages":msgs or [],"case_messages":links or []})
    f=ce._find_case_for_message(client=c,account_id="acc-y",thread_id=thread,normalized_subject=ce.normalize_subject(subj),workspace_id="w",event_key=event_key,received_at=None,own_message=own,reply_ids=reply_ids)
    return f["id"] if f else None
def case(i,subj,status="in_progress",thread="t-old",ek=None):
    return {"id":i,"account_id":"acc-y","workspace_id":"w","primary_thread_id":thread,"normalized_subject":ce.normalize_subject(subj),"status":status,"metadata":{"event_key":ek} if ek else {},"last_activity_at":"2026-10-01"}

R={}
G="no-reply@accounts.google.com"
R[1]=classify(M(G,"Alerta de seguridad","Se detectó un inicio de sesión nuevo. ¿Fuiste tú? Confirma la actividad: Sí / No"))
R[2]=classify(M(G,"Alerta de seguridad","Se otorgó acceso a una app a tu cuenta. No necesitas hacer nada."))
R[3]=classify(M("facturacion@proveedor-x.mx","Recibo de pago","Tu pago fue recibido. Saldo $0.00. Pagada."))
fail=case("C-fail","Cargo fallido en tu tarjeta",ek=None)
R["4a"]=classify(M("facturacion@proveedor-x.mx","Recibo de pago","Pago recibido ref TX-123. Pagada."),existing=fail)
R["4b"]={"caso_asociado":find([fail],"Recibo de pago",thread="t-new"),"nota":"buscar en case_engine/case_repository cierre automatico por recibo"}
R[5]={"caso_asociado_mismo_asunto_otra_entidad":find([case("C-f2","Pago")],"Pago",thread="t-otro")}
R[7]={"nota":"no existe lógica de días/seguimiento en el motor; ver rg"}
R["8"]=classify(M("propia-1@yahoo.example","Hola","Te comparto la foto.",labels=("SENT",),to=["amigo@ext.com"]))
R["7_envio_peticion"]=classify(M("propia-1@yahoo.example","Cotización","¿Me puedes enviar la cotización antes del viernes? Por favor confirma.",labels=("SENT",),to=["cliente@ext.com"]))
R["9a_yahoo_a_gmail_vista_desde_gmail"]=classify(M("propia-1@yahoo.example","Pendiente","Por favor revisa y paga la factura antes del viernes, urgente.",to=["propia2@gmail.com"]),acc=GMAIL)
R["9b_mayus_espacios"]=classify(M("  Propia-1@YAHOO.example ","Nota","Por favor paga la factura urgente.",labels=("SENT","INBOX"),to=["propia-1@yahoo.example"]))
R["9c_alias_gmail"]={"normalize('p.ropia2+x@gmail.com')":normalize_address("p.ropia2+x@gmail.com")}
R["9d_apropia2"]=classify(M("no-confirmada@gmail.example","Pendiente","Por favor paga la factura urgente."),acc=GMAIL)
R[10]={k:classify(M(s,sub,b)) for k,(s,sub,b) in {"railway":("notifications@railway.app","Deploy failed","Your deployment failed. Please check the build logs and fix the error."),"github_ci":("notifications@github.com","[repo] Run failed: CI","The workflow run failed. Action required: review."),"respaldo":("backup@servidor.mx","Respaldo fallido","El respaldo nocturno falló, por favor revisa urgente.")}.items()}
R[11]=classify(M(G,"Nuevo inicio de sesión","Se inició sesión en tu cuenta desde Windows. Si fuiste tú, no necesitas hacer nada."))
R[12]=classify(M(G,"Actividad sospechosa","Bloqueamos un intento de inicio de sesión sospechoso desde Rusia. Revisa la actividad y cambia tu contraseña."))
sub=case("C-sub","Suscripción Netflix")
R["13a"]=classify(M("info@netflix.com","Cancelación confirmada","Tu suscripción fue cancelada."),existing=sub)
R["13b"]={"caso_asociado":find([sub],"Cancelación confirmada",thread="t-n")}
R[14]={"caso_asociado_mismo_asunto":find([case("C-gym","Cancelación confirmada")],"Cancelación confirmada",thread="t-otro")}
R[15]={"factura_B_asociada_a":find([case("C-A","Factura disponible")],"Factura disponible",thread="t-B")}
R[16]={"cerrado_reabierto_o_asociado":find([case("C-closed","Factura disponible",status="closed")],"Re: Factura disponible",thread="t-new")}
R[17]={"mismo_hilo":find([case("C-h","Asunto X",thread="t-1")],"Re: Asunto distinto",thread="t-1"),
       "propio_por_in_reply_to":find([case("C-r","Y",thread="t-1")],"Re: Y",thread=None,own=True,reply_ids=["<p1@x>"],msgs=[{"id":"m1","account_id":"acc-y","internet_message_id":"<p1@x>"}],links=[{"message_id":"m1","case_id":"C-r"}]),
       "entrante_con_in_reply_to_sin_hilo":find([case("C-r","Y",thread="t-1")],"otro asunto",thread=None,own=False,reply_ids=["<p1@x>"],msgs=[{"id":"m1","account_id":"acc-y","internet_message_id":"<p1@x>"}],links=[{"message_id":"m1","case_id":"C-r"}])}
R[18]={"clasif":classify(M("persona@ext.com","Hola","ok")),"caso_asociado_asunto_generico":find([case("C-g","Hola")],"Hola",thread="t-z")}
print(json.dumps(R,ensure_ascii=False,indent=1,default=str))
