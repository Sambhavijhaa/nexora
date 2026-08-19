import { Link } from "react-router-dom";

const page: React.CSSProperties = { minHeight: "100svh", background: "#0b0d12", color: "#f5f7fb", display: "flex", flexDirection: "column", overflowX: "hidden" };
const nav: React.CSSProperties = { minHeight: 76, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 clamp(18px,6vw,88px)", background: "#11141b", borderBottom: "1px solid #252b36" };
const brand: React.CSSProperties = { color: "#f5f7fb", textDecoration: "none", fontSize: 21, fontWeight: 800, display: "flex", alignItems: "center", gap: 9 };

export default function Landing() {
  return <main style={page}>
    <nav style={nav}>
      <Link to="/" style={brand}><span style={{width:34,height:34,borderRadius:9,display:"grid",placeItems:"center",background:"#7c5cff",color:"#fff",fontSize:14}}>N</span>Nexora</Link>
      <div style={{display:"flex",alignItems:"center",gap:6}}><Link to="/login" style={{color:"#f5f7fb",textDecoration:"none",fontSize:14,fontWeight:700,padding:"10px 12px"}}>Sign in</Link><Link to="/register" style={{color:"#fff",background:"#7c5cff",textDecoration:"none",fontSize:14,fontWeight:700,padding:"10px 13px",borderRadius:8}}>Create account</Link></div>
    </nav>
    <section style={{flex:1,width:"100%",maxWidth:1180,margin:"0 auto",padding:"clamp(60px,12vh,130px) clamp(20px,6vw,70px) 60px",boxSizing:"border-box"}}>
      <div style={{maxWidth:760}}><p style={{margin:"0 0 14px",color:"#9b7bff",fontSize:12,fontWeight:800,letterSpacing:".12em",textTransform:"uppercase"}}>Nexora workspace</p><h1 style={{margin:0,color:"#f5f7fb",fontSize:"clamp(44px,8vw,82px)",lineHeight:1.03,letterSpacing:"-.055em",fontWeight:800}}>Move work forward,<br/>together<span style={{color:"#9b7bff"}}>.</span></h1><p style={{margin:"22px 0 0",maxWidth:520,color:"#aeb6c5",fontSize:"clamp(16px,2vw,19px)",lineHeight:1.6}}>Projects, people, and progress in one place.</p></div>
    </section>
    <footer style={{padding:"12px 18px",color:"#667083",background:"#11141b",borderTop:"1px solid #252b36",fontSize:11,textAlign:"center"}}>© 2026 Nexora</footer>
    <style>{`@media(max-width:560px){nav{min-height:64px!important;padding:0 12px!important}nav a{font-size:13px!important}nav a:first-child{font-size:18px!important}nav a:first-child span{width:30px!important;height:30px!important}section{padding:58px 20px 40px!important}h1{font-size:clamp(40px,12vw,54px)!important}footer{font-size:10px!important}}`}</style>
  </main>;
}
