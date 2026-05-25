/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState, useMemo, ReactNode } from 'react';
import { 
  LayoutDashboard, 
  UploadCloud, 
  History, 
  CheckCircle2, 
  AlertCircle, 
  FileText, 
  Search, 
  User, 
  LogOut, 
  ChevronRight, 
  Download, 
  Filter, 
  BarChart3, 
  X,
  RefreshCw,
  Bell,
  Menu,
  MoreVertical,
  ArrowLeft,
  Calendar,
  Database
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

// --- Types ---
type View = 
  | 'login' 
  | 'supplier_home' 
  | 'upload' 
  | 'errors' 
  | 'supplier_history' 
  | 'admin_dashboard' 
  | 'shipment_detail' 
  | 'validated_data';

type UserRole = 'supplier' | 'admin';

interface ShipmentHistory {
  id: string;
  fileName: string;
  period: string;
  version: number;
  status: 'valid' | 'invalid' | 'replaced' | 'canceled' | 'processed';
  sentAt: string;
  validRows: number;
  invalidRows: number;
  supplierName?: string;
}

// --- Mock Data ---

const MOCK_SHIPMENTS: ShipmentHistory[] = [
  { id: 'UP-001', fileName: 'forecast_vianmaq_maio.xlsx', period: '2026-05', version: 1, status: 'replaced', sentAt: '2026-05-03 10:22', validRows: 120, invalidRows: 0, supplierName: 'Vianmaq' },
  { id: 'UP-002', fileName: 'forecast_vianmaq_maio_v2.xlsx', period: '2026-05', version: 2, status: 'valid', sentAt: '2026-05-04 09:10', validRows: 124, invalidRows: 0, supplierName: 'Vianmaq' },
  { id: 'UP-003', fileName: 'forecast_vianmaq_junho.xlsx', period: '2026-06', version: 1, status: 'invalid', sentAt: '2026-05-04 14:33', validRows: 0, invalidRows: 8, supplierName: 'Vianmaq' },
  { id: 'UP-004', fileName: 'dist_uberlandia_maio.csv', period: '2026-05', version: 1, status: 'valid', sentAt: '2026-05-04 11:45', validRows: 88, invalidRows: 0, supplierName: 'Distribuidor Uberlândia' },
  { id: 'UP-005', fileName: 'fornecedor_x_maio.xlsx', period: '2026-05', version: 1, status: 'invalid', sentAt: '2026-05-04 14:33', validRows: 0, invalidRows: 8, supplierName: 'Fornecedor X' },
  { id: 'UP-006', fileName: 'fornecedor_y_maio.xlsx', period: '2026-05', version: 1, status: 'canceled', sentAt: '2026-05-03 17:02', validRows: 0, invalidRows: 0, supplierName: 'Fornecedor Y' },
];

const MOCK_ERRORS = [
  { line: 15, column: 'material_code', value: '', error: 'Campo obrigatório', correction: 'Informar código do material' },
  { line: 22, column: 'forecast_quantity', value: 'ABC', error: 'Tipo inválido', correction: 'Informar valor numérico' },
  { line: 31, column: 'forecast_period', value: '32/13/2026', error: 'Data inválida', correction: 'Usar formato válido de data' },
];

const MOCK_VALIDATED_DATA = [
  { supplier: 'Vianmaq', branch: 'Marialva', code: '600-319-3610', desc: 'Filtro Hidráulico', period: '2026-05', qty: 57, version: 2, date: '04/05/2026', file: 'forecast_vianmaq_maio_v2.xlsx' },
  { supplier: 'Vianmaq', branch: 'Marialva', code: '600-319-3750', desc: 'Elemento Filtrante', period: '2026-05', qty: 42, version: 2, date: '04/05/2026', file: 'forecast_vianmaq_maio_v2.xlsx' },
  { supplier: 'Vianmaq', branch: 'Marialva', code: '20Y-60-31211', desc: 'Filtro de Ar', period: '2026-05', qty: 31, version: 2, date: '04/05/2026', file: 'forecast_vianmaq_maio_v2.xlsx' },
];

// --- Sub-components ---

const StatusBadge = ({ status }: { status: ShipmentHistory['status'] }) => {
  const configs = {
    valid: { bg: 'bg-green-100', text: 'text-green-700', label: 'Válido/Ativo' },
    invalid: { bg: 'bg-red-100', text: 'text-red-700', label: 'Inválido' },
    replaced: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Substituído' },
    canceled: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Cancelado' },
    processed: { bg: 'bg-komatsu-navy/10', text: 'text-komatsu-navy', label: 'Processado' },
  };
  const config = configs[status];
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${config.bg} ${config.text}`}>
      {config.label}
    </span>
  );
};

export default function App() {
  const [view, setView] = useState<View>('login');
  const [role, setRole] = useState<UserRole>('supplier');

  const handleLogin = (selectedRole: UserRole) => {
    setRole(selectedRole);
    setView(selectedRole === 'supplier' ? 'supplier_home' : 'admin_dashboard');
  };

  const Sidebar = () => (
    <aside className="w-60 bg-white border-r border-gray-200 flex flex-col h-screen fixed left-0 top-0 z-20">
      <div className="p-6 border-b border-gray-100 bg-komatsu-navy">
        <h1 className="text-3xl font-black tracking-tighter font-display flex items-center gap-2 text-komatsu-yellow">
          KOMATSU
        </h1>
      </div>
      
      <nav className="flex-1 p-4 space-y-1">
        <div className="px-3 py-2 text-[10px] font-bold text-gray-400 uppercase tracking-widest">{role === 'supplier' ? 'Fornecedor' : 'Administrativo'}</div>
        {role === 'supplier' ? (
          <>
            <button onClick={() => setView('supplier_home')} className={`w-full flex items-center gap-3 px-3 py-2 rounded-md transition-colors text-sm ${view === 'supplier_home' ? 'bg-komatsu-gray text-komatsu-navy font-bold shadow-sm' : 'text-gray-600 hover:bg-gray-50'}`}>
              <LayoutDashboard size={18} /> Dashboard
            </button>
            <button onClick={() => setView('upload')} className={`w-full flex items-center gap-3 px-3 py-2 rounded-md transition-colors text-sm ${view === 'upload' ? 'bg-komatsu-gray text-komatsu-navy font-bold shadow-sm' : 'text-gray-600 hover:bg-gray-50'}`}>
              <UploadCloud size={18} /> Enviar Arquivo
            </button>
            <button onClick={() => setView('supplier_history')} className={`w-full flex items-center gap-3 px-3 py-2 rounded-md transition-colors text-sm ${view === 'supplier_history' ? 'bg-komatsu-gray text-komatsu-navy font-bold shadow-sm' : 'text-gray-600 hover:bg-gray-50'}`}>
              <History size={18} /> Meus Envios
            </button>
          </>
        ) : (
          <>
            <button onClick={() => setView('admin_dashboard')} className={`w-full flex items-center gap-3 px-3 py-2 rounded-md transition-colors text-sm ${view === 'admin_dashboard' ? 'bg-komatsu-gray text-komatsu-navy font-bold shadow-sm' : 'text-gray-600 hover:bg-gray-50'}`}>
              <BarChart3 size={18} /> Painel de Controle
            </button>
            <button onClick={() => setView('validated_data')} className={`w-full flex items-center gap-3 px-3 py-2 rounded-md transition-colors text-sm ${view === 'validated_data' ? 'bg-komatsu-gray text-komatsu-navy font-bold shadow-sm' : 'text-gray-600 hover:bg-gray-50'}`}>
              <Database size={18} /> Dados Validados
            </button>
          </>
        )}
      </nav>

      <div className="p-4 border-t border-gray-100 bg-gray-50/50">
        <div className="bg-blue-50 p-3 rounded-lg border border-blue-100 mb-4">
          <p className="text-[10px] font-bold text-blue-800 uppercase mb-1">Janela de Maio</p>
          <div className="flex items-center gap-2">
            <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
              <div className="bg-komatsu-navy h-full" style={{ width: '85%' }}></div>
            </div>
            <span className="text-[10px] font-bold text-blue-800">85%</span>
          </div>
          <p className="text-[10px] text-blue-600 mt-1 italic">Encerra em 05/05/2026</p>
        </div>
        
        <button onClick={() => setView('login')} className="w-full flex items-center gap-3 px-3 py-2 rounded-md hover:bg-red-50 text-red-500 transition-colors text-sm font-semibold">
          <LogOut size={18} /> Sair do Portal
        </button>
      </div>
    </aside>
  );

  const Header = ({ title }: { title: string }) => (
    <header className="h-16 bg-komatsu-navy border-b border-komatsu-border-navy flex items-center justify-between px-6 sticky top-0 z-20 ml-60">
      <div className="flex items-center gap-8 text-white">
        <h1 className="text-[#FFCD00] text-3xl font-black tracking-tighter">KOMATSU</h1>
        <div className="h-6 w-px bg-white/20"></div>
        <h2 className="text-white font-medium text-lg">{title}</h2>
      </div>
      
      <div className="flex items-center gap-4">
        <div className="text-right mr-2">
          <p className="text-white text-xs font-semibold">{role === 'supplier' ? 'Vianmaq S.A.' : 'Komatsu Corp'}</p>
          <p className="text-white/60 text-[10px]">{role === 'supplier' ? 'joao.vianmaq@email.com' : 'admin.komatsu@email.com'}</p>
        </div>
        <div className="w-10 h-10 rounded-full bg-komatsu-yellow flex items-center justify-center font-bold text-komatsu-navy shadow-lg ring-2 ring-white/10">
          {role === 'supplier' ? 'JV' : 'AK'}
        </div>
      </div>
    </header>
  );

  // --- View Components ---

  if (view === 'login') {
    return (
      <div className="min-h-screen flex items-center justify-center p-6 bg-komatsu-gray">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-xl shadow-xl border border-gray-200 p-8 w-full max-w-md"
        >
          <div className="text-center mb-8 bg-komatsu-navy p-6 -m-8 mb-8 rounded-t-xl">
            <h1 className="text-4xl font-extrabold tracking-tighter font-display text-komatsu-yellow">
              KOMATSU
            </h1>
            <p className="mt-2 text-white/60 text-xs font-medium uppercase tracking-widest">Portal de Coleta e Validação</p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1 tracking-widest">Acesso ao Portal</label>
              <input 
                type="email" 
                placeholder="exemplo@email.com" 
                className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:outline-none focus:ring-1 focus:ring-komatsu-navy transition bg-gray-50 text-sm"
                defaultValue={role === 'supplier' ? 'joao.vianmaq@email.com' : 'admin.komatsu@email.com'}
              />
            </div>
            <div>
              <input 
                type="password" 
                placeholder="Senha de acesso" 
                className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:outline-none focus:ring-1 focus:ring-komatsu-navy transition bg-gray-50 text-sm"
              />
            </div>
            
            <div className="grid grid-cols-1 gap-3 pt-2">
              <button 
                onClick={() => handleLogin('supplier')}
                className="w-full bg-komatsu-yellow hover:brightness-95 text-komatsu-navy font-black text-xs uppercase tracking-widest py-4 rounded shadow-sm transition"
              >
                Entrar como Fornecedor
              </button>
              <button 
                onClick={() => handleLogin('admin')}
                className="w-full bg-white border border-gray-200 text-gray-400 hover:text-komatsu-navy hover:border-komatsu-navy font-bold text-xs uppercase tracking-widest py-3 rounded transition"
              >
                Acesso Administrativo
              </button>
            </div>
            
            <p className="text-center text-[10px] text-gray-400 mt-6 leading-relaxed border-t border-gray-100 pt-4">
              &copy; 2024 Komatsu | Uso Restrito <br/>
              TI Operações
            </p>
          </div>
        </motion.div>
      </div>
    );
  }

  const Layout = ({ children, title }: { children: ReactNode, title: string }) => (
    <div className="min-h-screen bg-komatsu-gray flex flex-col overflow-hidden">
      <Sidebar />
      <Header title={title || "Portal de Coleta e Validação de Forecast"} />
      <main className="ml-60 flex-1 overflow-y-auto p-6 space-y-6">
        <AnimatePresence mode="wait">
          <motion.div
            key={view}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            {children}
          </motion.div>
        </AnimatePresence>
        
        <footer className="h-8 bg-gray-100/50 border-t border-gray-200 flex items-center justify-between px-4 text-[10px] text-gray-400 font-medium rounded-t-lg">
          <p>&copy; 2024 Komatsu | Portal de Coleta e Validação | MVP v1.0</p>
          <p className="flex gap-4">
            <span className="hover:text-komatsu-navy cursor-pointer">Privacidade</span>
            <span className="hover:text-komatsu-navy cursor-pointer">Termos de Uso</span>
            <span className="hover:text-komatsu-navy cursor-pointer font-bold">Suporte: TI Operações</span>
          </p>
        </footer>
      </main>
    </div>
  );

  // View: Supplier Home
  if (view === 'supplier_home') {
    return (
      <Layout title="Dashboard do Fornecedor">
        <div className="mb-8">
          <h3 className="text-2xl font-bold text-gray-900">Olá, Vianmaq</h3>
          <p className="text-gray-500">Seja bem-vindo ao portal de coleta de forecast.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
            <p className="text-[10px] font-bold text-gray-400 uppercase mb-2">Último Envio</p>
            <p className="text-lg font-bold text-komatsu-navy">04/05/2026</p>
            <p className="text-[10px] text-gray-400 mt-1">às 09:10</p>
          </div>
          <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
            <p className="text-[10px] font-bold text-gray-400 uppercase mb-2">Status Atual</p>
            <div className="flex items-center justify-between">
              <span className="text-lg font-bold text-komatsu-navy">Válido</span>
              <span className="px-2 py-0.5 bg-green-100 text-green-700 text-[10px] font-bold rounded uppercase">Ativo</span>
            </div>
          </div>
          <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
            <p className="text-[10px] font-bold text-gray-400 uppercase mb-2">Versão do Forecast</p>
            <p className="text-lg font-bold text-komatsu-navy">v.2 (Maio)</p>
          </div>
          <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
            <p className="text-[10px] font-bold text-gray-400 uppercase mb-2">Linhas Processadas</p>
            <p className="text-lg font-bold text-komatsu-navy">124 <span class="text-xs font-normal text-gray-400">/ 0 erros</span></p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-6">
              <h4 className="font-bold text-lg">Ações Rápidas</h4>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <button 
                onClick={() => setView('upload')}
                className="flex flex-col items-center justify-center p-6 rounded-xl border-2 border-dashed border-gray-200 hover:border-komatsu-yellow hover:bg-komatsu-yellow/5 transition-all group"
              >
                <div className="p-3 bg-komatsu-navy text-white rounded-full mb-3 group-hover:scale-110 transition">
                  <UploadCloud size={24} />
                </div>
                <span className="font-bold text-sm text-komatsu-navy">Enviar Forecast</span>
              </button>
              
              <button className="flex flex-col items-center justify-center p-6 rounded-xl border-2 border-dashed border-gray-200 hover:border-komatsu-navy hover:bg-komatsu-navy/5 transition-all group">
                <div className="p-3 bg-gray-100 text-gray-600 rounded-full mb-3 group-hover:bg-komatsu-navy group-hover:text-white transition">
                  <Download size={24} />
                </div>
                <span className="font-bold text-sm text-gray-600 group-hover:text-komatsu-navy">Baixar Template</span>
              </button>

              <button 
                onClick={() => setView('supplier_history')}
                className="flex flex-col items-center justify-center p-6 rounded-xl border-2 border-dashed border-gray-200 hover:border-komatsu-navy hover:bg-komatsu-navy/5 transition-all group"
              >
                <div className="p-3 bg-gray-100 text-gray-600 rounded-full mb-3 group-hover:bg-komatsu-navy group-hover:text-white transition">
                  <Search size={24} />
                </div>
                <span className="font-bold text-sm text-gray-600 group-hover:text-komatsu-navy">Ver Histórico</span>
              </button>
            </div>
          </div>

          <div className="bg-komatsu-navy rounded-xl shadow-sm p-6 text-white relative overflow-hidden">
            <div className="relative z-10">
              <h4 className="font-bold text-lg mb-4 flex items-center gap-2">
                <AlertCircle size={20} className="text-komatsu-yellow" />
                Aviso de Privacidade
              </h4>
              <p className="text-sm opacity-80 leading-relaxed">
                Este sistema utiliza visibilidade restrita. Você visualiza apenas as movimentações e históricos relacionados ao seu CNPJ (Vianmaq).
              </p>
              <div className="mt-8 pt-8 border-t border-white/10">
                <p className="text-[10px] uppercase font-bold tracking-widest text-komatsu-yellow">Versão do Sistema</p>
                <p className="text-xl font-display mt-1">v1.2.0-MVP</p>
              </div>
            </div>
            {/* Abstract industry pattern */}
            <div className="absolute -bottom-4 -right-4 opacity-10 blur-xl">
               <Database size={160} />
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  // View: Upload
  if (view === 'upload') {
    return (
      <Layout title="Submeter Novo Forecast">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
            <div className="mb-8">
              <h4 className="text-lg font-bold mb-2">Importar Arquivo</h4>
              <p className="text-sm text-gray-500">Envie o arquivo consolidado para processamento e validação.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
              <div className="p-4 bg-gray-50 border border-gray-200 rounded-xl">
                <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1">Tipo de Relatório</label>
                <div className="flex items-center gap-2">
                  <FileText size={18} className="text-komatsu-navy" />
                  <span className="font-bold text-komatsu-navy">Forecast DB (Distribuidores)</span>
                </div>
              </div>
              <div className="p-4 bg-gray-50 border border-gray-200 rounded-xl">
                <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1">Período de Referência</label>
                <div className="flex items-center gap-2">
                  <Calendar size={18} className="text-komatsu-navy" />
                  <span className="font-bold text-komatsu-navy">2026 - Maio</span>
                </div>
              </div>
            </div>

            <div className="border-4 border-dashed border-gray-100 rounded-3xl p-12 text-center hover:border-komatsu-yellow hover:bg-komatsu-yellow/5 transition-all cursor-pointer group mb-8">
              <div className="mx-auto w-16 h-16 bg-komatsu-navy text-white rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition">
                <UploadCloud size={32} />
              </div>
              <h5 className="font-bold text-xl mb-2 text-komatsu-navy">Arraste e solte seu arquivo aqui</h5>
              <p className="text-sm text-gray-400">ou clique para selecionar (xlsx, csv)</p>
              <p className="mt-8 inline-block px-4 py-1 bg-gray-50 rounded-full text-[10px] font-bold text-gray-400 uppercase tracking-widest">Limite: 50MB</p>
            </div>

            <div className="bg-gray-50 rounded-xl p-6 mb-8">
              <h6 className="text-[10px] font-bold text-gray-400 uppercase mb-4 tracking-widest flex items-center gap-2">
                <CheckCircle2 size={14} /> Validações Automáticas
              </h6>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-y-3 gap-x-6">
                {[
                  'Extensão do arquivo', 'Aba esperada', 'Colunas obrigatórias',
                  'Tipos de dados', 'Campos nulos', 'Datas válidas',
                  'Quantidade numérica', 'Material preenchido', 'Fornecedor compatível'
                ].map((item, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs text-gray-600">
                    <div className="w-1.5 h-1.5 bg-green-500 rounded-full"></div>
                    {item}
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-end gap-4">
              <button 
                onClick={() => setView('supplier_home')}
                className="px-6 py-3 font-bold text-gray-500 hover:text-komatsu-navy transition"
              >
                Cancelar
              </button>
              <button 
                onClick={() => setView('errors')}
                className="px-8 py-3 bg-komatsu-yellow text-komatsu-navy font-bold rounded-xl shadow-lg hover:bg-yellow-400 transition transform active:scale-95"
              >
                Validar Forecast
              </button>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  // View: Errors
  if (view === 'errors') {
    return (
      <Layout title="Relatório de Erros - UP-003">
        <div className="bg-red-50 border border-red-200 rounded-2xl p-6 mb-8 flex items-start gap-4">
          <div className="p-3 bg-red-100 text-red-600 rounded-full">
            <X size={24} />
          </div>
          <div>
            <h4 className="text-red-800 font-bold text-lg">Arquivo Inválido</h4>
            <p className="text-red-700 text-sm">Foram encontrados {MOCK_ERRORS.length} erros críticos no seu arquivo. Corrija-os e reenvie para processamento.</p>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="p-6 border-b border-gray-100 flex items-center justify-between">
            <h4 className="font-bold text-gray-900">Detalhamento das Inconsistências</h4>
            <button className="flex items-center gap-2 px-4 py-2 bg-komatsu-navy text-white rounded-lg font-bold text-sm hover:bg-komatsu-navy/90 transition">
              <Download size={16} /> Baixar Relatório de Correção
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-gray-50 text-[10px] font-bold text-gray-400 uppercase tracking-widest border-b border-gray-100">
                  <th className="px-6 py-4">Linha</th>
                  <th className="px-6 py-4">Coluna</th>
                  <th className="px-6 py-4">Valor Informado</th>
                  <th className="px-6 py-4">Erro Detectado</th>
                  <th className="px-6 py-4">Orientação</th>
                </tr>
              </thead>
              <tbody className="text-sm divide-y divide-gray-100">
                {MOCK_ERRORS.map((err, i) => (
                  <tr key={i} className="hover:bg-gray-50 transition">
                    <td className="px-6 py-4 font-mono font-bold text-komatsu-navy">{err.line}</td>
                    <td className="px-6 py-4 font-semibold">{err.column}</td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 bg-gray-100 rounded border border-gray-200 text-xs text-gray-600">
                        {err.value || '(vazio)'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-red-600 font-medium">{err.error}</td>
                    <td className="px-6 py-4 text-gray-500 italic uppercase text-[10px]">{err.correction}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <p className="text-center text-xs text-gray-400 mt-8 italic">
          Nota: O arquivo original permanece inalterado no repositório de temporários. Somente arquivos 100% válidos são persistidos na camada Trusted.
        </p>

        <div className="mt-8 flex justify-center">
           <button 
             onClick={() => setView('upload')}
             className="px-8 py-3 bg-komatsu-navy text-white font-bold rounded-xl shadow-lg hover:bg-komatsu-navy/90 transition flex items-center gap-2"
           >
             <ArrowLeft size={18} /> Tentar Novamente
           </button>
        </div>
      </Layout>
    );
  }

  // View: History
  if (view === 'supplier_history') {
    return (
      <Layout title="Histórico de Envios">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="p-6 border-b border-gray-100 flex items-center justify-between">
            <h4 className="font-bold text-gray-900">Rastreabilidade de Arquivos</h4>
            <div className="flex gap-2">
              <button className="p-2 hover:bg-gray-100 rounded-lg text-gray-400 border border-gray-200">
                <Filter size={18} />
              </button>
              <div className="relative">
                <Search size={18} className="absolute left-3 top-2.5 text-gray-400" />
                <input type="text" placeholder="Filtrar por nome..." className="pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-komatsu-navy" />
              </div>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-gray-50 text-[10px] font-bold text-gray-400 uppercase tracking-widest border-b border-gray-100">
                  <th className="px-6 py-4">Upload ID</th>
                  <th className="px-6 py-4">Arquivo</th>
                  <th className="px-6 py-4">Período</th>
                  <th className="px-6 py-4 text-center">Versão</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Data Envio</th>
                  <th className="px-6 py-4 text-center">Ação</th>
                </tr>
              </thead>
              <tbody className="text-sm divide-y divide-gray-100">
                {MOCK_SHIPMENTS.filter(s => s.supplierName === 'Vianmaq').map((s) => (
                  <tr key={s.id} className="hover:bg-gray-50 transition cursor-pointer" onClick={() => setView('shipment_detail')}>
                    <td className="px-6 py-4 font-mono font-bold text-blue-600">{s.id}</td>
                    <td className="px-6 py-4 font-medium max-w-xs truncate">{s.fileName}</td>
                    <td className="px-6 py-4 font-semibold text-komatsu-navy">{s.period}</td>
                    <td className="px-6 py-4 text-center">
                      <span className="w-6 h-6 flex items-center justify-center bg-gray-100 rounded text-xs font-bold">{s.version}</span>
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={s.status} />
                    </td>
                    <td className="px-6 py-4 text-gray-400 text-xs">{s.sentAt}</td>
                    <td className="px-6 py-4 text-center">
                      {s.status === 'valid' ? (
                        <button className="text-red-400 hover:text-red-600 font-bold text-[10px] uppercase underline decoration-2 underline-offset-4">Cancelar</button>
                      ) : (
                        <ChevronRight size={16} className="mx-auto text-gray-300" />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Layout>
    );
  }

  // View: Admin Dashboard
  if (view === 'admin_dashboard') {
    return (
      <Layout title="Painel Administrativo de Coleta">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
          {[
            { label: 'Esperados', val: 12, color: 'navy' },
            { label: 'Enviaram', val: 8, color: 'blue' },
            { label: 'Pendentes', val: 4, color: 'yellow' },
            { label: 'Válidos', val: 6, color: 'green' },
            { label: 'Com Erro', val: 2, color: 'red' },
            { label: 'Cancelados', val: 1, color: 'gray' },
          ].map((item, i) => (
            <div key={i} className="bg-white p-4 rounded-xl shadow-sm border border-gray-200 border-b-2 border-b-komatsu-navy">
              <p className="text-[10px] font-bold text-gray-400 uppercase mb-1">{item.label}</p>
              <p className="text-2xl font-bold text-komatsu-navy">{item.val}</p>
            </div>
          ))}
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden mb-8">
          <div className="p-6 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
            <h4 className="font-bold text-gray-900">Status por Fornecedor</h4>
            <div className="flex gap-2">
              <select className="px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-xs font-bold text-gray-600 focus:outline-none">
                <option>Maio 2026</option>
              </select>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-gray-50 text-[10px] font-bold text-gray-400 uppercase tracking-widest border-b border-gray-100">
                  <th className="px-6 py-4">Fornecedor</th>
                  <th className="px-6 py-4">Período</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Último Envio</th>
                  <th className="px-6 py-4 text-center">Versão</th>
                  <th className="px-6 py-4 text-center">Erros</th>
                  <th className="px-6 py-4 text-center">Ação</th>
                </tr>
              </thead>
              <tbody className="text-sm divide-y divide-gray-100">
                {[
                  { name: 'Vianmaq', period: '2026-05', status: 'valid', last: '04/05/2026 09:10', version: 2, errors: 0 },
                  { name: 'Distribuidor Uberlândia', period: '2026-05', status: 'valid', last: '04/05/2026 11:45', version: 1, errors: 0 },
                  { name: 'Fornecedor X', period: '2026-05', status: 'invalid', last: '04/05/2026 14:33', version: 1, errors: 8 },
                  { name: 'Fornecedor Y', period: '2026-05', status: 'canceled', last: '03/05/2026 17:02', version: 1, errors: 0 },
                  { name: 'Mecânica Centro', period: '2026-05', status: 'none', last: '-', version: '-', errors: '-' },
                ].map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50 transition border-l-4 border-transparent hover:border-komatsu-navy">
                    <td className="px-6 py-4 font-bold text-komatsu-navy">{row.name}</td>
                    <td className="px-6 py-4 font-semibold text-gray-500">{row.period}</td>
                    <td className="px-6 py-4">
                      {row.status === 'none' ? (
                        <span className="px-2 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-400">Pendente</span>
                      ) : (
                        <StatusBadge status={row.status as any} />
                      )}
                    </td>
                    <td className="px-6 py-4 text-xs text-gray-400">{row.last}</td>
                    <td className="px-6 py-4 text-center font-mono font-bold text-gray-400">{row.version}</td>
                    <td className="px-6 py-4 text-center">
                      {row.errors ? <span className="text-red-500 font-bold">{row.errors}</span> : <span className="text-gray-200">-</span>}
                    </td>
                    <td className="px-6 py-4 text-center">
                      {row.status === 'none' ? (
                        <button className="px-3 py-1 bg-komatsu-yellow text-komatsu-navy rounded-lg text-[10px] font-bold uppercase shadow-sm active:scale-95 transition">Notificar</button>
                      ) : (
                        <button onClick={() => setView('shipment_detail')} className="text-komatsu-navy hover:text-blue-600 text-xs font-bold underline underline-offset-2">Ver Detalhe</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-komatsu-yellow/10 border border-komatsu-yellow/20 rounded-2xl p-6 mb-8">
           <p className="text-xs text-komatsu-navy leading-relaxed font-medium">
             <span className="font-extrabold uppercase mr-2">NOTA MVP:</span>
             As notificações para fornecedores pendentes são manuais nesta fase. O sistema permite baixar a lista de e-mails para envio centralizado. Integração via AWS SES prevista para v2.0.
           </p>
        </div>
      </Layout>
    );
  }

  // View: Shipment Detail
  if (view === 'shipment_detail') {
    return (
      <Layout title="Auditoria de Envio - UP-002">
        <button onClick={() => setView(role === 'supplier' ? 'supplier_history' : 'admin_dashboard')} className="mb-6 flex items-center gap-2 text-gray-500 hover:text-komatsu-navy font-bold text-sm transition">
          <ArrowLeft size={16} /> Voltar
        </button>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-8 pb-6 border-b border-gray-100">
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 bg-green-50 text-green-600 rounded-2xl flex items-center justify-center">
                    <CheckCircle2 size={32} />
                  </div>
                  <div>
                    <h4 className="text-2xl font-bold text-komatsu-navy">UP-002</h4>
                    <p className="text-sm text-gray-400 font-mono">forecast_vianmaq_maio_v2.xlsx</p>
                  </div>
                </div>
                <StatusBadge status="valid" />
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-8">
                 <div>
                    <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1">Fornecedor</label>
                    <p className="font-bold text-komatsu-navy">Vianmaq</p>
                 </div>
                 <div>
                    <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1">Período</label>
                    <p className="font-bold text-komatsu-navy">2026-05</p>
                 </div>
                 <div>
                    <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1">Versão</label>
                    <span className="w-6 h-6 inline-flex items-center justify-center bg-gray-100 rounded text-xs font-bold">2</span>
                 </div>
                 <div>
                    <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1">Enviado por</label>
                    <p className="font-bold text-komatsu-navy text-sm">joao.vianmaq@email.com</p>
                 </div>
                 <div>
                    <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1">Data/Hora</label>
                    <p className="font-bold text-komatsu-navy text-sm">04/05/2026 09:10</p>
                 </div>
                 <div>
                    <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1">Tabela Destino</label>
                    <p className="font-mono text-xs text-blue-600 font-bold">TRUSTED.forecast_validated</p>
                 </div>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h4 className="font-bold mb-6 flex items-center gap-2 uppercase text-xs tracking-widest text-gray-400">
                <RefreshCw size={14} /> Ciclo de Vida do Dado
              </h4>
              <div className="flex items-center justify-between px-4">
                {[
                  { label: 'Recebido', done: true },
                  { label: 'Validado', done: true },
                  { label: 'Normalizado', done: true },
                  { label: 'Publicado', done: true },
                ].map((step, i, arr) => (
                  <div key={i} className="flex flex-col items-center flex-1 relative">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center z-10 ${step.done ? 'bg-komatsu-navy text-white' : 'bg-gray-100 text-gray-400'}`}>
                      {step.done ? <CheckCircle2 size={16} /> : <span className="text-[10px] font-bold">{i+1}</span>}
                    </div>
                    <span className={`text-[10px] font-bold uppercase mt-2 ${step.done ? 'text-komatsu-navy' : 'text-gray-400'}`}>{step.label}</span>
                    {i < arr.length - 1 && (
                      <div className="absolute top-4 left-1/2 w-full h-[2px] bg-gray-100">
                         <div className={`h-full ${arr[i+1].done ? 'bg-komatsu-navy' : 'bg-transparent'}`} style={{ width: '100%' }}></div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 border-b-4 border-komatsu-yellow">
              <h4 className="font-bold mb-4 uppercase text-xs tracking-widest text-gray-400">Sumário do Processo</h4>
              <div className="space-y-4">
                 <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <span className="text-sm text-gray-500">Linhas Totais</span>
                    <span className="text-lg font-bold text-komatsu-navy">124</span>
                 </div>
                 <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                    <span className="text-sm text-green-700">Linhas Válidas</span>
                    <span className="text-lg font-bold text-green-700">124</span>
                 </div>
                 <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg opacity-40">
                    <span className="text-sm text-gray-500">Linhas Inválidas</span>
                    <span className="text-lg font-bold text-gray-500">0</span>
                 </div>
              </div>

              {role === 'admin' && (
                <button className="w-full mt-6 py-3 border-2 border-komatsu-navy text-komatsu-navy font-bold rounded-xl hover:bg-komatsu-navy hover:text-white transition flex items-center justify-center gap-2 active:scale-95">
                  <RefreshCw size={18} /> Reprocessar Lote
                </button>
              )}
            </div>

            <div className="p-4 bg-komatsu-navy text-white rounded-2xl">
               <h5 className="font-bold text-sm mb-2 opacity-60 uppercase tracking-widest">Rastreabilidade SQL</h5>
               <code className="text-[10px] block p-2 bg-black/20 rounded font-mono break-all opacity-80">
                 SELECT * FROM raw.stg_forecast <br/>
                 WHERE upload_id = 'UP-002' <br/>
                 AND supplier_id = 'VIANMAQ_001'
               </code>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  // View: Validated Data
  if (view === 'validated_data') {
    return (
      <Layout title="Consulta de Dados Validados">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-4 lg:grid-cols-5 gap-4">
            <div>
              <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1">Fornecedor</label>
              <select className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-600 focus:outline-none focus:ring-1 focus:ring-komatsu-navy">
                <option>Vianmaq</option>
                <option>Todos</option>
              </select>
            </div>
            <div>
              <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1">Filial</label>
              <select className="px-3 py-2 w-full bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-600 focus:outline-none">
                <option>Todas</option>
                <option>Marialva</option>
              </select>
            </div>
            <div>
              <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1">Material</label>
              <input type="text" placeholder="Código..." className="px-3 py-2 w-full bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-600 focus:outline-none" />
            </div>
            <div>
              <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1">Período</label>
              <select className="px-3 py-2 w-full bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-600 focus:outline-none">
                <option>Maio 2026</option>
                <option>Junho 2026</option>
              </select>
            </div>
            <div className="flex items-end">
              <button className="w-full py-2 bg-komatsu-navy text-white rounded-lg font-bold text-sm shadow-lg hover:bg-komatsu-navy/90 active:scale-95 transition flex items-center justify-center gap-2">
                <Search size={16} /> Filtrar
              </button>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="p-6 border-b border-gray-100 flex items-center justify-between">
            <h4 className="font-bold text-gray-900">Forecast Consolidado (Trusted)</h4>
            <div className="flex gap-2">
               <button className="flex items-center gap-2 px-4 py-2 text-sm font-bold text-gray-500 hover:text-komatsu-navy">
                  <Download size={16} /> CSV
               </button>
               <button className="flex items-center gap-2 px-4 py-2 text-sm font-bold text-gray-500 hover:text-komatsu-navy">
                  <Download size={16} /> XLSX
               </button>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-gray-50 text-[10px] font-bold text-gray-400 uppercase tracking-widest border-b border-gray-100">
                  <th className="px-6 py-4">Fornecedor</th>
                  <th className="px-6 py-4">Filial</th>
                  <th className="px-6 py-4">Cód. Mat.</th>
                  <th className="px-6 py-4">Descrição</th>
                  <th className="px-6 py-4">Período</th>
                  <th className="px-6 py-4 text-center">Quant.</th>
                  <th className="px-6 py-4 text-center">Ver.</th>
                  <th className="px-6 py-4">Data Proc.</th>
                </tr>
              </thead>
              <tbody className="text-sm divide-y divide-gray-100 italic font-mono text-[11px]">
                {MOCK_VALIDATED_DATA.map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50 transition border-l-4 border-transparent hover:border-blue-400">
                    <td className="px-6 py-4 font-bold text-komatsu-navy not-italic font-sans text-xs">{row.supplier}</td>
                    <td className="px-6 py-4">{row.branch}</td>
                    <td className="px-6 py-4 font-bold">{row.code}</td>
                    <td className="px-6 py-4 truncate max-w-xs">{row.desc}</td>
                    <td className="px-6 py-4 text-blue-600 font-bold">{row.period}</td>
                    <td className="px-6 py-4 text-center text-lg text-komatsu-navy font-sans font-bold not-italic">{row.qty}</td>
                    <td className="px-6 py-4 text-center">
                       <span className="px-2 py-0.5 bg-gray-100 rounded text-[10px] font-bold">{row.version}</span>
                    </td>
                    <td className="px-6 py-4 text-gray-400">{row.date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="mt-8 p-6 bg-white rounded-2xl border border-gray-200">
           <div className="flex items-center gap-4">
              <div className="p-3 bg-komatsu-yellow/20 text-komatsu-navy rounded-xl">
                 <BarChart3 size={24} />
              </div>
              <div>
                 <h5 className="font-bold text-komatsu-navy">Visão Analítica</h5>
                 <p className="text-sm text-gray-500 italic">Esta tela provê uma consulta operacional rápida. Para análises de tendência e BI, utilize o dashboard oficial no Power BI.</p>
              </div>
              <button className="ml-auto px-6 py-2 bg-komatsu-yellow text-komatsu-navy font-bold rounded-lg shadow active:scale-95 transition">Abrir Power BI</button>
           </div>
        </div>
      </Layout>
    );
  }

  return null;
}