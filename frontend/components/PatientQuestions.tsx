"use client";
import { useState } from "react";
import Link from "next/link";
import { MessageCircle, Send, BookOpen } from "lucide-react";
import { queryRag } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export default function PatientQuestions(){
 const {user,loading:authLoading}=useAuth();
 const [question,setQuestion]=useState('');const [busy,setBusy]=useState(false);const [result,setResult]=useState<any>(null);const [error,setError]=useState('');
 const suggestions=['Tôi cần ghi lại những gì khi đo đường huyết?','Tôi nên chuẩn bị gì cho lần tái khám?','Tôi muốn tìm hiểu cách chăm sóc bàn chân.'];
 async function submit(e:React.FormEvent){e.preventDefault();if(!user||busy||!question.trim())return;setBusy(true);setError('');setResult(null);try{setResult(await queryRag(question,5,user.id));}catch{setError('Chưa kết nối được với trợ lý. Bạn có thể thử lại sau. Nếu cần hỗ trợ y tế, hãy liên hệ bác sĩ.');}finally{setBusy(false);}}
 return <div className="mx-auto max-w-3xl space-y-7"><div><p className="eyebrow">CÙNG HIỂU RÕ HƠN</p><h1 className="mt-3 text-3xl font-semibold">Bạn muốn hỏi điều gì?</h1><p className="mt-3 text-slate-600 dark:text-slate-300">Hỏi về việc theo dõi đường huyết và chăm sóc bản thân. Trợ lý cung cấp thông tin tham khảo, không chẩn đoán hay thay đổi thuốc cho bạn.</p></div>
 {!authLoading&&!user&&<Card className="p-6">Bạn cần <Link href="/login" className="underline font-semibold">đăng nhập</Link> để gửi câu hỏi.</Card>}
 <Card className="p-6 sm:p-8"><form onSubmit={submit}><label htmlFor="patient-question" className="font-semibold flex gap-2 items-center"><MessageCircle aria-hidden/> Câu hỏi của bạn</label><textarea id="patient-question" value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Bạn có thể viết bằng lời của mình…" rows={5} maxLength={3000} required className="mt-4 w-full rounded-2xl border border-slate-300 bg-transparent"/><div className="mt-4 flex justify-end"><Button type="submit" disabled={!user||busy||!question.trim()} size="lg"><Send aria-hidden/>{busy?'Đang tìm thông tin…':'Gửi câu hỏi'}</Button></div></form></Card>
 {!result&&!busy&&<section><h2 className="font-semibold mb-3">Hoặc bắt đầu từ một câu hỏi gợi ý</h2><div className="grid gap-3">{suggestions.map(text=><button key={text} onClick={()=>{setQuestion(text);document.getElementById('patient-question')?.focus();}} className="rounded-2xl border border-slate-300 p-4 text-left hover:bg-white dark:hover:bg-slate-800">{text}</button>)}</div></section>}
 {error&&<p role="alert" className="rounded-2xl border border-red-300 bg-red-50 p-5 text-red-800">{error}</p>}
 {busy&&<p role="status">Đang tìm thông tin phù hợp với câu hỏi của bạn…</p>}
 {result&&<Card className="p-6 sm:p-8">{result.status==='pending_review'?<><h2 className="text-xl font-semibold">Câu hỏi đang được chuyên gia xem lại</h2><p className="mt-3">Bạn có thể theo dõi câu trả lời đã duyệt trong <Link href="/my/reviews" className="underline">Lịch sử tư vấn</Link>.</p></>:<><h2 className="text-xl font-semibold">Thông tin dành cho bạn</h2><div className="mt-5 whitespace-pre-wrap leading-loose">{result.answer}</div>{result.contexts?.length>0&&<details className="mt-6 border-t pt-4"><summary className="cursor-pointer min-h-12 font-semibold">Xem tài liệu tham khảo</summary><ul className="space-y-3 mt-3">{result.contexts.map((c:any,i:number)=><li key={i}><BookOpen className="inline mr-2" aria-hidden size={18}/>{c.file_name||c.source_id||`Tài liệu ${i+1}`}{c.page?` · trang ${c.page}`:''}</li>)}</ul></details>}</>}</Card>}
 </div>;
}