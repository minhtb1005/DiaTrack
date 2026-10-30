"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { medicationPlans, createMedicationPlan, approveMedicationPlan, recordMedicationDose, stopMedicationPlan } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Plan = { events?:{action:string;reason:string;created_at:string}[]; id:string; medicine:string; prescribed_dose:string; prescription_reference:string; status:string; doctor_id:string; times:string[]; start_date:string; end_date:string; schedule:{due_at:string;status:string}[]; adherence:{due:number;taken:number;rate:number|null} };
export default function MedicationsPage() {
  const {user,loading}=useAuth();
  const [patient,setPatient]=useState("");
  const [plans,setPlans]=useState<Plan[]>([]);
  const [error,setError]=useState("");
  const [busy,setBusy]=useState(false);
  const [notice,setNotice]=useState("");
  const doctor=user?.role==="doctor";
  const target=doctor?patient:user?.id;
  async function load() {
    if(!target) return;
    setError("");setBusy(true);
    try {setPlans((await medicationPlans(target)).plans);} catch(e) {setError("Chưa tải được lịch thuốc. Kiểm tra bệnh nhân đã chọn và thử lại.");} finally {setBusy(false);}
  }
  useEffect(()=>{if(!user||doctor) return; load(); const timer=setInterval(load,60000); return ()=>clearInterval(timer);},[user?.id]);
  async function action(run:()=>Promise<unknown>, message:string) {
    setBusy(true);setError("");setNotice("");
    try {await run();setNotice(message);await load();} catch(e) {setError("Chưa lưu được thay đổi. Kiểm tra thông tin, cập nhật lịch rồi thử lại.");} finally {setBusy(false);}
  }
  if(loading)return <p role="status">Đang tải…</p>;
  if(!user)return <Card className="p-8">Cần <Link href="/login" className="underline">đăng nhập</Link> để xem lịch thuốc.</Card>;
  return <div className="space-y-6">
    <div><h1 className="text-2xl font-bold">Lịch thuốc đã duyệt</h1><p className="mt-2 text-slate-600 dark:text-slate-300">Theo giờ Việt Nam. Chỉ dùng theo đơn bác sĩ; không tự đổi liều hoặc uống bù khi bỏ liều.</p></div>
    {doctor&&<Card className="p-5 space-y-4"><h2 className="font-semibold">Bác sĩ tạo lịch từ đơn thuốc</h2>
      <label className="block">Mã bệnh nhân<Input value={patient} onChange={e=>{setPatient(e.target.value);setPlans([]);setNotice("");}} required /></label>
      <Button onClick={load} disabled={busy||!patient}>Xem lịch bệnh nhân</Button>
      <form className="grid gap-4 sm:grid-cols-2" onSubmit={e=>{
        e.preventDefault();const form=new FormData(e.currentTarget);
        action(()=>createMedicationPlan({patient_id:patient,medicine:String(form.get("medicine")),prescribed_dose:String(form.get("dose")),prescription_reference:String(form.get("reference")),times:String(form.get("times")).split(",").map(t=>t.trim()),start_date:String(form.get("start")),end_date:String(form.get("end"))}),"Đã lưu bản nháp. Kiểm tra lại trước khi duyệt.");
      }}>
        <label>Tên thuốc theo đơn<Input name="medicine" required maxLength={200}/></label>
        <label>Liều và cách dùng theo đơn<Input name="dose" required maxLength={300}/></label>
        <label>Mã hoặc nguồn đơn thuốc<Input name="reference" required maxLength={300}/></label>
        <label>Giờ nhắc (HH:MM, cách nhau dấu phẩy)<Input name="times" placeholder="08:00, 20:00" required/></label>
        <label>Ngày bắt đầu<Input name="start" type="date" required/></label>
        <label>Ngày kết thúc<Input name="end" type="date" required/></label>
        <Button type="submit" disabled={busy||!patient}>Lưu bản nháp</Button>
      </form>
    </Card>}
    {error&&<div role="alert" className="rounded-xl border border-red-300 bg-red-50 p-4 text-red-800">{error}</div>}
    {notice&&<p role="status">{notice}</p>}
    {!doctor&&<Button onClick={load} disabled={busy}>Cập nhật lịch</Button>}
    {busy&&<p role="status">Đang xử lý…</p>}
    {!busy&&!plans.length&&!error&&<Card className="p-6">Chưa có lịch thuốc được hiển thị. Bệnh nhân chỉ thấy lịch sau khi bác sĩ duyệt.</Card>}
    {plans.map(plan=><Card key={plan.id} className="p-5 space-y-3">
      <h2 className="text-lg font-semibold">{plan.medicine}</h2><p>{plan.prescribed_dose}</p>
      <p className="text-sm">Nguồn đơn: {plan.prescription_reference} · {plan.start_date} đến {plan.end_date} · {plan.times.join(", ")} (giờ Việt Nam)</p>
      <p>{plan.status==="draft"?"Bản nháp — chưa áp dụng":plan.status==="stopped"?"Bác sĩ đã dừng lịch này":"Bác sĩ đã duyệt"}</p>
      {doctor&&plan.status==="draft"&&plan.doctor_id===user.id&&<Button disabled={busy} onClick={()=>action(()=>approveMedicationPlan(plan.id),"Đã duyệt lịch thuốc.")}>Duyệt lịch theo đơn</Button>}
      {plan.status==="stopped"&&plan.events?.filter(e=>e.action==="stopped").map(e=><p key={e.created_at}>Lý do dừng: {e.reason}</p>)}
      {doctor&&plan.status==="approved"&&plan.doctor_id===user.id&&<details className="border-t pt-3"><summary className="cursor-pointer min-h-12">Dừng lịch theo quyết định bác sĩ</summary><form className="space-y-3" onSubmit={e=>{e.preventDefault();const reason=String(new FormData(e.currentTarget).get('reason'));action(()=>stopMedicationPlan(plan.id,reason),"Đã dừng lịch. Các lần xác nhận trước đó vẫn được lưu.");}}><label className="block">Lý do dừng<Input name="reason" required maxLength={500}/></label><Button disabled={busy} variant="outline" type="submit">Xác nhận dừng lịch</Button></form></details>}
      {plan.status==="approved"&&<>
        <p>Đã xác nhận dùng {plan.adherence.taken}/{plan.adherence.due} liều đến hạn{plan.adherence.rate!==null?` (${Math.round(plan.adherence.rate*100)}%)`:" — chưa có liều đến hạn"}. Chưa phản hồi không đồng nghĩa đã bỏ liều.</p>
        <ul className="divide-y">{plan.schedule.map(dose=><li key={dose.due_at} className="flex flex-wrap items-center justify-between gap-3 py-3">
          <span>{new Date(dose.due_at).toLocaleString("vi-VN",{timeZone:"Asia/Ho_Chi_Minh"})} — {({taken:"Đã dùng",skipped:"Đã báo bỏ liều",overdue:"Đến hạn — chưa xác nhận",scheduled:"Chưa đến giờ"} as Record<string,string>)[dose.status]}</span>
          {user.role==="user"&&dose.status==="overdue"&&<div className="flex gap-2"><Button disabled={busy} onClick={()=>action(()=>recordMedicationDose(plan.id,dose.due_at,"taken"),"Đã ghi nhận dùng thuốc.")}>Đã dùng</Button><Button variant="outline" disabled={busy} onClick={()=>action(()=>recordMedicationDose(plan.id,dose.due_at,"skipped"),"Đã ghi nhận bỏ liều. Hỏi bác sĩ/dược sĩ, không tự uống bù.")}>Bỏ liều</Button></div>}
        </li>)}</ul>
      </>}
    </Card>)}
  </div>;
}