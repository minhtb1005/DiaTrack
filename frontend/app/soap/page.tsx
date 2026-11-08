"use client";

import {useState} from "react";
import {useAuth} from "@/lib/auth";
import {API_BASE,createSoapDraft,editSoapDraft,getSoapDraft,reviewSoapDraft,signSoapDraft} from "@/lib/api";
import {Button} from "@/components/ui/button";
import {Card} from "@/components/ui/card";
import {Input} from "@/components/ui/input";

export default function SoapPage(){
  const {user}=useAuth();
  const [patient,setPatient]=useState("");
  const [noteId,setNoteId]=useState("");
  const [transcript,setTranscript]=useState("");
  const [note,setNote]=useState<any>();
  const [review,setReview]=useState<any>();
  const [error,setError]=useState("");
  const clinician=["doctor","admin"].includes(user?.role||"");
  const target=user?.role==="user"?user.id:patient;
  async function run(fn:()=>Promise<any>){try{setError("");const value=await fn();setNote(value);setNoteId(value.id);setReview(undefined)}catch(e){setError(String(e))}}
  async function transcribe(file?:File){if(!file)return;try{setError("");const form=new FormData();form.append("audio",file);const res=await fetch(`${API_BASE}/v1/voice/transcribe`,{method:"POST",credentials:"include",body:form});if(!res.ok)throw new Error(`transcribe failed ${res.status}`);const data=await res.json();setTranscript(data.text||"");if(!data.text)setError("Không nhận được nội dung; vui lòng nhập transcript thủ công.")}catch(e){setError(String(e))}}
  async function loadReview(){try{setError("");setReview(await reviewSoapDraft(noteId))}catch(e){setError(String(e))}}
  function exportPdf(){window.location.href=`${API_BASE}/v1/soap/drafts/${noteId}/export`}
  return <div className="space-y-5"><h1 className="text-2xl font-bold">Hồ sơ SOAP</h1><p>Nháp hỗ trợ bác sĩ, không phải chẩn đoán. Plan chỉ do bác sĩ nhập.</p>
    <Card className="space-y-3 p-5">{user?.role!=="user"&&<label>Mã bệnh nhân<Input value={patient} onChange={e=>setPatient(e.target.value)}/></label>}<label>Mã hồ sơ<Input value={noteId} onChange={e=>setNoteId(e.target.value)}/></label><Button disabled={!noteId} onClick={()=>run(()=>getSoapDraft(noteId))}>Mở hồ sơ</Button><label>Audio buổi khám<Input aria-label="Audio buổi khám" type="file" accept="audio/wav,audio/webm,audio/mpeg" onChange={e=>transcribe(e.target.files?.[0])}/></label><label>Transcript<textarea className="min-h-32 w-full rounded-lg border p-3" value={transcript} onChange={e=>setTranscript(e.target.value)}/></label><Button disabled={!target||!transcript} onClick={()=>run(()=>createSoapDraft({patient_id:target,transcript}))}>Tạo nháp</Button></Card>
    {error&&<p role="alert">{error}</p>}
    {note&&<Card className="space-y-3 p-5" data-testid="soap-draft"><label>S<textarea aria-label="Subjective" className="w-full rounded border p-2" value={note.subjective} disabled={!clinician||note.status==="signed"} onChange={e=>setNote({...note,subjective:e.target.value})}/></label><label>O<textarea aria-label="Objective" className="w-full rounded border p-2" value={note.objective} disabled={!clinician||note.status==="signed"} onChange={e=>setNote({...note,objective:e.target.value})}/></label><label>A<textarea aria-label="Assessment" className="w-full rounded border p-2" value={note.assessment} disabled={!clinician||note.status==="signed"} onChange={e=>setNote({...note,assessment:e.target.value})}/></label><label>Plan<textarea aria-label="Plan" className="w-full rounded border p-2" value={note.plan} disabled={!clinician||note.status==="signed"} onChange={e=>setNote({...note,plan:e.target.value})}/></label><p>Thiếu: {note.missing?.join(", ")||"không"}</p>{clinician&&<Button onClick={loadReview}>Kiểm tra hồ sơ</Button>}{clinician&&note.status==="draft"&&<><Button onClick={()=>run(()=>editSoapDraft(note.id,{subjective:note.subjective,objective:note.objective,assessment:note.assessment,plan:note.plan}))}>Lưu chỉnh sửa</Button><Button onClick={()=>run(()=>signSoapDraft(note.id))}>Ký duyệt</Button></>}{clinician&&note.status==="signed"&&<Button onClick={exportPdf}>Xuất PDF bàn giao</Button>}</Card>}
    {review&&<Card className="space-y-3 p-5" data-testid="soap-review"><h2 className="font-semibold">Kiểm tra trước khi ký</h2><p>Thuốc đã duyệt: {review.clinical_checks.approved_medications.join(", ")||"chưa ghi nhận"}</p><p>HbA1c: {review.clinical_checks.hba1c||"chưa ghi nhận"}</p><p>{review.clinical_checks.warning}</p><a className="underline" href={review.icd_suggestions[0].source} target="_blank" rel="noreferrer">{review.icd_suggestions[0].code} — {review.icd_suggestions[0].label}</a><p>Thay đổi: {review.diff.length}</p><p>Audit: {review.audit.map((x:any)=>x.action).join(" → ")}</p></Card>}
  </div>
}
