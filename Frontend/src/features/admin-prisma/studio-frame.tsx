import { createRoot } from 'react-dom/client';
import StudioFrame from './StudioFrame';
import '@prisma/studio-core/ui/index.css';
import './studio-frame.css';

createRoot(document.getElementById('root')!).render(<StudioFrame />);
