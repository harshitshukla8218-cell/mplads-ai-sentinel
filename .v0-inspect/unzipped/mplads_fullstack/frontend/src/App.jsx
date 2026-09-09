import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar.jsx'
import Dashboard from './pages/Dashboard.jsx'
import ProjectDetail from './pages/ProjectDetail.jsx'
import Entities from './pages/Entities.jsx'
import About from './pages/About.jsx'

export default function App() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 min-w-0">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/project/:workId" element={<ProjectDetail />} />
          <Route path="/entities" element={<Entities />} />
          <Route path="/about" element={<About />} />
        </Routes>
      </main>
    </div>
  )
}
