import { useEffect } from "react";
import { Routes, Route, useLocation } from "react-router-dom";
import Navbar from "./components/Navbar.jsx";
import Home from "./pages/Home.jsx";
import RegisterCase from "./pages/RegisterCase.jsx";
import ReportSighting from "./pages/ReportSighting.jsx";
import TrackCase from "./pages/TrackCase.jsx";
import Admin from "./pages/Admin.jsx";
import MatchReport from "./pages/admin/MatchReport.jsx";

export default function App() {
  const { pathname } = useLocation();
  useEffect(() => window.scrollTo(0, 0), [pathname]);
  return (
    <>
      <Navbar />
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/register" element={<RegisterCase />} />
          <Route path="/report" element={<ReportSighting />} />
          <Route path="/track" element={<TrackCase />} />
          <Route path="/admin" element={<Admin />} />
          <Route path="/admin/report/:matchId" element={<MatchReport />} />
          <Route path="*" element={<Home />} />
        </Routes>
      </main>
      <footer>
        <p><strong>Code4Cause</strong> · Govt. Women's Institute of Technology · Major Project 2026</p>
        <p className="small">AI suggestions are only leads. Every match is reviewed by a trained person before anyone is contacted.</p>
      </footer>
    </>
  );
}
