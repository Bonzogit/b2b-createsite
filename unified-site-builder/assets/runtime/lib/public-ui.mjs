// Fixed public interface copy. Visitor input is never part of this content.
export const uiEntries=[
 ['products','Products','产品'],['articles','Articles','文章'],['contact','Contact','联系我们'],['home','Home','首页'],
 ['request','Request information','提交询盘'],['name','Name','姓名'],['email','Email','邮箱'],['message','Message','需求内容'],
 ['attachment','Attachment (PDF/JPG/PNG, up to 5 MB)','附件（PDF/JPG/PNG，最大5 MB）'],['send','Send inquiry','提交询盘'],
 ['saved','Inquiry saved. Reference:','询盘已保存，编号：'],['sendFailed','Unable to submit. Please try again.','提交失败，请重试。']
];
export const publicUI={kind:'ui',status:'published',revision:1,context:'Public website interface',blocks:uiEntries.map(([key,text])=>({id:'ui#'+key,text}))};
export const chineseUI=Object.fromEntries(uiEntries.map(([key,,zh])=>['ui#'+key,zh]));

// Interface labels are authored, including legitimate cognates such as French "Articles".
const labels={
 es:['Productos','Artículos','Contacto','Inicio','Solicitar información','Nombre','Correo electrónico','Mensaje','Adjunto (PDF/JPG/PNG, hasta 5 MB)','Enviar consulta','Consulta guardada. Referencia:','No se pudo enviar. Inténtalo de nuevo.'],
 ar:['المنتجات','المقالات','اتصل بنا','الرئيسية','طلب معلومات','الاسم','البريد الإلكتروني','الرسالة','مرفق (PDF/JPG/PNG، حتى 5 MB)','إرسال الاستفسار','تم حفظ الاستفسار. الرقم:','تعذر الإرسال. يرجى المحاولة مرة أخرى.'],
 ru:['Продукты','Статьи','Контакты','Главная','Запросить информацию','Имя','Электронная почта','Сообщение','Вложение (PDF/JPG/PNG, до 5 MB)','Отправить запрос','Запрос сохранён. Номер:','Не удалось отправить. Попробуйте ещё раз.'],
 fr:['Produits','Articles','Contact','Accueil','Demander des informations','Nom','Adresse e-mail','Message','Pièce jointe (PDF/JPG/PNG, jusqu’à 5 MB)','Envoyer une demande','Demande enregistrée. Référence :','Envoi impossible. Veuillez réessayer.'],
 de:['Produkte','Artikel','Kontakt','Startseite','Informationen anfordern','Name','E-Mail','Nachricht','Anhang (PDF/JPG/PNG, bis zu 5 MB)','Anfrage senden','Anfrage gespeichert. Referenz:','Senden fehlgeschlagen. Bitte erneut versuchen.'],
 pt:['Produtos','Artigos','Contato','Início','Solicitar informações','Nome','E-mail','Mensagem','Anexo (PDF/JPG/PNG, até 5 MB)','Enviar consulta','Consulta salva. Referência:','Não foi possível enviar. Tente novamente.']
};
export const authoredUI={zh:chineseUI,...Object.fromEntries(Object.entries(labels).map(([lang,values])=>[lang,Object.fromEntries(uiEntries.map(([key],i)=>['ui#'+key,values[i]]))]))};
