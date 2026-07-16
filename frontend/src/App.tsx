import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import ReviewList from './components/ReviewList';
import ReviewDetail from './components/ReviewDetail';
import ReviewForm from './components/ReviewForm';
import EvalReport from './components/EvalReport';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<ReviewList />} />
          <Route path="reviews/new" element={<ReviewForm />} />
          <Route path="reviews/:id" element={<ReviewDetail />} />
          <Route path="eval" element={<EvalReport />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
