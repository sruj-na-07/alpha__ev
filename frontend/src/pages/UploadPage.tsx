import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { Upload, FileSpreadsheet, ArrowRight, AlertCircle, Check, ChevronDown } from 'lucide-react';
import toast from 'react-hot-toast';
import Alphi from '../components/Alphi';
import { uploadFile, getColumns, mapColumns, type ColumnInfo } from '../api';

const REQUIRED_FIELDS = ['review_text'];
const OPTIONAL_FIELDS = ['review_id', 'rating', 'date', 'source', 'reviewer', 'location', 'charger_type'];

export default function UploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [datasetId, setDatasetId] = useState<string | null>(null);
  const [columnInfo, setColumnInfo] = useState<ColumnInfo | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [step, setStep] = useState<'upload' | 'mapping' | 'confirm'>('upload');

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const f = acceptedFiles[0];
    if (!f) return;
    
    const ext = f.name.split('.').pop()?.toLowerCase();
    if (!['csv', 'xlsx', 'xls'].includes(ext || '')) {
      toast.error('Please upload a CSV or XLSX file');
      return;
    }
    if (f.size > 50 * 1024 * 1024) {
      toast.error('File size must be under 50MB');
      return;
    }

    setFile(f);
    setUploading(true);

    try {
      const dataset = await uploadFile(f);
      setDatasetId(dataset.id);
      const cols = await getColumns(dataset.id);
      setColumnInfo(cols);
      setMapping(cols.suggested_mapping || {});
      setStep('mapping');
      toast.success('File uploaded successfully!');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Upload failed');
      setFile(null);
    } finally {
      setUploading(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    maxFiles: 1,
    disabled: uploading,
  });

  const handleMapColumn = (targetField: string, sourceColumn: string) => {
    setMapping(prev => {
      const next = { ...prev };
      if (sourceColumn === '') {
        delete next[targetField];
      } else {
        next[targetField] = sourceColumn;
      }
      return next;
    });
  };

  const handleConfirmMapping = async () => {
    if (!mapping.review_text) {
      toast.error('You must map the review text column');
      return;
    }
    if (!datasetId) return;

    try {
      await mapColumns(datasetId, mapping);
      setStep('confirm');
      toast.success('Column mapping saved');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to save mapping');
    }
  };

  const handleStartPipeline = () => {
    if (datasetId) {
      navigate(`/dataset/${datasetId}/clean`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Upload Dataset</h2>
          <p className="text-gray-500 mt-1">Feed Alphi your EV charging reviews</p>
        </div>
        <Alphi mood={uploading ? 'excited' : step === 'confirm' ? 'happy' : 'idle'} size="sm" />
      </div>

      {/* Step indicators */}
      <div className="flex items-center gap-2 text-sm">
        {['Upload File', 'Map Columns', 'Confirm & Process'].map((label, i) => {
          const stepNames = ['upload', 'mapping', 'confirm'];
          const currentIdx = stepNames.indexOf(step);
          const isActive = i === currentIdx;
          const isDone = i < currentIdx;
          return (
            <div key={label} className="flex items-center gap-2">
              {i > 0 && <div className={`w-8 h-0.5 ${isDone ? 'bg-teal-500' : 'bg-gray-200'}`} />}
              <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium ${isActive ? 'bg-teal-100 text-teal-700' : isDone ? 'bg-teal-500 text-white' : 'bg-gray-100 text-gray-400'}`}>
                {isDone ? <Check size={12} /> : <span>{i + 1}</span>}
                {label}
              </div>
            </div>
          );
        })}
      </div>

      {/* Upload step */}
      {step === 'upload' && (
        <div className="card">
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
              isDragActive ? 'border-teal-400 bg-teal-50' : 'border-gray-200 hover:border-teal-300 hover:bg-gray-50'
            } ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            <input {...getInputProps()} />
            <div className="flex flex-col items-center gap-3">
              {uploading ? (
                <>
                  <Alphi mood="excited" size="md" message="Alphi is munching on your data... 🐱" />
                  <div className="w-48 h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div className="h-full bg-teal-500 rounded-full animate-pulse" style={{ width: '60%' }} />
                  </div>
                </>
              ) : (
                <>
                  <Upload size={40} className="text-gray-300" />
                  <div>
                    <p className="text-lg font-medium text-gray-700">
                      {isDragActive ? 'Drop your file here!' : 'Drag & drop your CSV or XLSX file'}
                    </p>
                    <p className="text-sm text-gray-400 mt-1">or click to browse · Max 50MB</p>
                  </div>
                </>
              )}
            </div>
          </div>

          {file && !uploading && (
            <div className="mt-4 flex items-center gap-3 p-3 bg-gray-50 rounded-xl">
              <FileSpreadsheet size={20} className="text-teal-600" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-700 truncate">{file.name}</p>
                <p className="text-xs text-gray-400">{(file.size / 1024).toFixed(1)} KB</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Mapping step */}
      {step === 'mapping' && columnInfo && (
        <div className="card space-y-6">
          <div>
            <h3 className="font-semibold text-gray-900 mb-1">Map Your Columns</h3>
            <p className="text-sm text-gray-500">Tell Alphi which column contains which data. Only review text is required.</p>
          </div>

          <div className="space-y-3">
            {[...REQUIRED_FIELDS, ...OPTIONAL_FIELDS].map(field => (
              <div key={field} className="flex items-center gap-4">
                <div className="w-40 flex items-center gap-1">
                  <span className="text-sm font-medium text-gray-700 capitalize">{field.replace(/_/g, ' ')}</span>
                  {REQUIRED_FIELDS.includes(field) && <span className="text-red-400 text-xs">*</span>}
                </div>
                <div className="relative flex-1">
                  <select
                    value={mapping[field] || ''}
                    onChange={e => handleMapColumn(field, e.target.value)}
                    className="input-field appearance-none pr-8"
                  >
                    <option value="">— Not mapped —</option>
                    {columnInfo.columns.map(col => (
                      <option key={col} value={col}>{col}</option>
                    ))}
                  </select>
                  <ChevronDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                </div>
              </div>
            ))}
          </div>

          {/* Preview */}
          {columnInfo.sample_rows.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Data Preview</h4>
              <div className="overflow-x-auto rounded-xl border border-gray-200">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      {columnInfo.columns.map(col => (
                        <th key={col} className="px-3 py-2 text-left font-medium text-gray-600 whitespace-nowrap">{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {columnInfo.sample_rows.slice(0, 5).map((row, i) => (
                      <tr key={i} className="border-t border-gray-100">
                        {columnInfo.columns.map(col => (
                          <td key={col} className="px-3 py-2 text-gray-700 max-w-[200px] truncate">{String(row[col] ?? '')}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="flex justify-end gap-3">
            <button onClick={() => setStep('upload')} className="btn-secondary">Back</button>
            <button onClick={handleConfirmMapping} className="btn-primary flex items-center gap-2">
              Confirm Mapping <ArrowRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Confirm step */}
      {step === 'confirm' && (
        <div className="card text-center py-10">
          <Alphi mood="excited" size="lg" message="Ready to analyze your reviews! Let's go! 🚀" />
          <div className="mt-6 space-y-3">
            <p className="text-gray-600">
              <strong>{file?.name}</strong> uploaded with column mapping configured.
            </p>
            <button onClick={handleStartPipeline} className="btn-primary text-lg px-8 py-3 inline-flex items-center gap-2 group">
              Start Cleaning
              <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
