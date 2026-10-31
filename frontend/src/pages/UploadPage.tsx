
import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import {
  UploadCloud,
  FileSpreadsheet,
  ArrowRight,
  Check,
  ChevronDown,
  ShieldCheck,
  Database,
  FileCheck2,
  Columns3,
  Sparkles,
  RefreshCw,
  Table2,
  CircleHelp,
  CheckCircle2,
  ArrowLeft,
  LockKeyhole,
} from 'lucide-react';
import toast from 'react-hot-toast';
import {
  uploadFile,
  getColumns,
  mapColumns,
  type ColumnDetectionResponse,
  type ColumnMappingRequest,
} from '../api';

interface FieldConfig {
  key: keyof ColumnMappingRequest;
  label: string;
  required: boolean;
  description: string;
}

const MAPPING_FIELDS: FieldConfig[] = [
  {
    key: 'text_column',
    label: 'Review Text',
    required: true,
    description: 'The main customer review or feedback text',
  },
  {
    key: 'rating_column',
    label: 'Rating / Score',
    required: false,
    description: 'Numeric rating, such as a 1–5 star score',
  },
  {
    key: 'date_column',
    label: 'Date / Timestamp',
    required: false,
    description: 'When the review was submitted',
  },
  {
    key: 'source_column',
    label: 'Source / Platform',
    required: false,
    description: 'Google, App Store, Play Store, etc.',
  },
  {
    key: 'reviewer_column',
    label: 'Reviewer / Author',
    required: false,
    description: 'Customer name or reviewer identifier',
  },
];

const STEPS = [
  { id: 'upload', label: 'Upload file', number: '01' },
  { id: 'mapping', label: 'Map columns', number: '02' },
  { id: 'confirm', label: 'Start analysis', number: '03' },
] as const;

export default function UploadPage() {
  const navigate = useNavigate();

  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [datasetId, setDatasetId] = useState<string | null>(null);
  const [columnInfo, setColumnInfo] =
    useState<ColumnDetectionResponse | null>(null);
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
      const uploadRes = await uploadFile(f);
      const newDatasetId = uploadRes.dataset_id;
      setDatasetId(newDatasetId);

      const cols = await getColumns(newDatasetId);
      setColumnInfo(cols);

      const initialMapping: Record<string, string> = {};

      if (cols.suggested_mapping) {
        Object.entries(cols.suggested_mapping).forEach(([k, v]) => {
          if (v) initialMapping[k] = v;
        });
      }

      setMapping(initialMapping);
      setStep('mapping');
      toast.success('File uploaded successfully!');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Upload failed');
      setFile(null);
    } finally {
      setUploading(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': [
        '.xlsx',
      ],
      'application/vnd.ms-excel': ['.xls'],
    },
    maxFiles: 1,
    disabled: uploading,
    noClick: true,
  });

  const handleMapColumn = (fieldKey: string, sourceCol: string) => {
    setMapping(prev => {
      const next = { ...prev };

      if (!sourceCol) {
        delete next[fieldKey];
      } else {
        next[fieldKey] = sourceCol;
      }

      return next;
    });
  };

  const handleConfirmMapping = async () => {
    if (!mapping.text_column) {
      toast.error('You must map the Review Text column');
      return;
    }

    if (!datasetId) return;

    try {
      const req: ColumnMappingRequest = {
        text_column: mapping.text_column,
        rating_column: mapping.rating_column || null,
        date_column: mapping.date_column || null,
        source_column: mapping.source_column || null,
        reviewer_column: mapping.reviewer_column || null,
      };

      await mapColumns(datasetId, req);
      setStep('confirm');
      toast.success('Column mapping saved successfully!');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to save mapping');
    }
  };

  const handleStartPipeline = () => {
    if (datasetId) {
      navigate(`/dataset/${datasetId}/clean`);
    }
  };

  const currentStepIndex = STEPS.findIndex(item => item.id === step);

  const formatFileSize = (size: number) => {
    if (size >= 1024 * 1024) {
      return `${(size / (1024 * 1024)).toFixed(2)} MB`;
    }
    return `${(size / 1024).toFixed(1)} KB`;
  };

  return (
    <main className="upload-page">
      <div className="upload-page-inner">

        {/* Header */}
        <header className="upload-header">
          <div>
            <div className="upload-eyebrow">
              <span className="upload-eyebrow-dot" />
              ALPHAEV DATA WORKSPACE
            </div>

            <h1 className="upload-heading">
              Bring your data.
              <span> Find the signal.</span>
            </h1>

            <p className="upload-subheading">
              Import EV charging reviews and transform customer feedback
              into structured, explainable intelligence.
            </p>
          </div>

          <div className="upload-header-note">
            <div className="upload-header-note-icon">
              <ShieldCheck size={18} />
            </div>
            <div>
              <strong>Secure data intake</strong>
              <span>Structured for analysis</span>
            </div>
          </div>
        </header>

        {/* Workflow */}
        <section className="upload-workflow">
          <div className="upload-workflow-top">
            <span className="upload-section-label">YOUR WORKFLOW</span>
            <span className="upload-step-count">
              STEP {currentStepIndex + 1} OF 3
            </span>
          </div>

          <div className="upload-step-track">
            {STEPS.map((item, index) => {
              const isActive = index === currentStepIndex;
              const isDone = index < currentStepIndex;

              return (
                <div
                  key={item.id}
                  className={`upload-step ${
                    isActive ? 'is-active' : ''
                  } ${isDone ? 'is-complete' : ''}`}
                >
                  <div className="upload-step-number">
                    {isDone ? <Check size={15} /> : item.number}
                  </div>

                  <div className="upload-step-copy">
                    <span>{item.label}</span>
                    <small>
                      {isDone
                        ? 'Completed'
                        : isActive
                        ? 'In progress'
                        : 'Up next'}
                    </small>
                  </div>

                  {index !== STEPS.length - 1 && (
                    <div
                      className={`upload-step-connector ${
                        isDone ? 'is-complete' : ''
                      }`}
                    />
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* Main content */}
        <div className="upload-main-layout">
          <section className="upload-main-panel">

            {/* STEP 1: UPLOAD */}
            {step === 'upload' && (
              <>
                <div className="upload-panel-heading">
                  <div>
                    <div className="upload-panel-kicker">
                      <Database size={14} />
                      DATASET IMPORT
                    </div>

                    <h2>Upload your dataset</h2>

                    <p>
                      Start with a CSV or Excel file containing EV charging
                      reviews.
                    </p>
                  </div>

                  <div className="upload-heading-index">01 / 03</div>
                </div>

                <div
                  {...getRootProps()}
                  className={`upload-dropzone ${
                    isDragActive ? 'is-dragging' : ''
                  } ${uploading ? 'is-uploading' : ''}`}
                >
                  <input {...getInputProps()} />

                  {uploading ? (
                    <div className="upload-progress-content">
                      <div className="upload-progress-icon">
                        <RefreshCw size={27} className="upload-spin" />
                      </div>

                      <h3>Preparing your dataset</h3>

                      <p>
                        Uploading your file and detecting its columns.
                        This may take a moment.
                      </p>

                      <div className="upload-progress-track">
                        <div className="upload-progress-bar" />
                      </div>

                      <span className="upload-progress-caption">
                        PROCESSING FILE
                      </span>
                    </div>
                  ) : (
                    <>
                      <div className="upload-dropzone-decoration">
                        <span />
                        <span />
                        <span />
                      </div>

                      <div className="upload-cloud-icon">
                        <UploadCloud size={31} strokeWidth={1.6} />
                      </div>

                      <h3>
                        {isDragActive
                          ? 'Drop your dataset here'
                          : 'Drag and drop your dataset'}
                      </h3>

                      <p className="upload-dropzone-description">
                        or browse files from your computer
                      </p>

                      <button
                        type="button"
                        className="upload-browse-button"
                        onClick={open}
                      >
                        Browse files
                        <ArrowRight size={16} />
                      </button>

                      <div className="upload-file-types">
                        <span>CSV</span>
                        <span>XLSX</span>
                        <span>XLS</span>
                        <i />
                        <span>Maximum file size: 50 MB</span>
                      </div>
                    </>
                  )}
                </div>

                <div className="upload-security-line">
                  <LockKeyhole size={14} />
                  <span>
                    Your dataset is uploaded directly to the AlphaEV
                    processing pipeline.
                  </span>
                </div>
              </>
            )}

            {/* STEP 2: COLUMN MAPPING */}
            {step === 'mapping' && columnInfo && (
              <>
                <div className="upload-panel-heading">
                  <div>
                    <div className="upload-panel-kicker">
                      <Columns3 size={14} />
                      DATA STRUCTURE
                    </div>

                    <h2>Map your columns</h2>

                    <p>
                      Match your dataset fields to the information AlphaEV
                      needs. Review Text is the only required field.
                    </p>
                  </div>

                  <div className="upload-heading-index">02 / 03</div>
                </div>

                {file && (
                  <div className="upload-selected-file">
                    <div className="upload-selected-file-icon">
                      <FileSpreadsheet size={20} />
                    </div>

                    <div className="upload-selected-file-info">
                      <strong>{file.name}</strong>
                      <span>{formatFileSize(file.size)} · Uploaded</span>
                    </div>

                    <CheckCircle2
                      size={19}
                      className="upload-file-success"
                    />
                  </div>
                )}

                <div className="upload-mapping-intro">
                  <div>
                    <strong>Detected dataset fields</strong>
                    <span>
                      {columnInfo.columns.length} columns identified
                    </span>
                  </div>

                  <div className="upload-detected-badge">
                    <Sparkles size={13} />
                    Auto-detected
                  </div>
                </div>

                <div className="upload-mapping-list">
                  {MAPPING_FIELDS.map(field => {
                    const isMapped = Boolean(mapping[field.key]);

                    return (
                      <div
                        key={field.key}
                        className={`upload-mapping-row ${
                          isMapped ? 'is-mapped' : ''
                        }`}
                      >
                        <div className="upload-mapping-field">
                          <div className="upload-mapping-field-title">
                            <span>{field.label}</span>

                            {field.required ? (
                              <span className="upload-required">
                                REQUIRED
                              </span>
                            ) : (
                              <span className="upload-optional">
                                OPTIONAL
                              </span>
                            )}
                          </div>

                          <p>{field.description}</p>
                        </div>

                        <div className="upload-select-wrap">
                          <select
                            value={mapping[field.key] || ''}
                            onChange={e =>
                              handleMapColumn(field.key, e.target.value)
                            }
                          >
                            <option value="">Not mapped</option>

                            {columnInfo.columns.map(col => (
                              <option key={col} value={col}>
                                {col}
                              </option>
                            ))}
                          </select>

                          <ChevronDown size={16} />
                        </div>

                        <div className="upload-mapping-status">
                          {isMapped ? (
                            <CheckCircle2 size={17} />
                          ) : field.required ? (
                            <CircleHelp size={17} />
                          ) : (
                            <span>—</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Preview */}
                {columnInfo.sample_preview &&
                  columnInfo.sample_preview.length > 0 && (
                    <div className="upload-preview-section">
                      <div className="upload-preview-heading">
                        <div>
                          <div className="upload-preview-title">
                            <Table2 size={16} />
                            Sample data preview
                          </div>
                          <p>Review a sample of your uploaded records.</p>
                        </div>

                        <span>
                          {Math.min(
                            columnInfo.sample_preview.length,
                            5
                          )}{' '}
                          ROWS
                        </span>
                      </div>

                      <div className="upload-preview-table-wrap">
                        <table className="upload-preview-table">
                          <thead>
                            <tr>
                              {columnInfo.columns.map(col => (
                                <th key={col}>{col}</th>
                              ))}
                            </tr>
                          </thead>

                          <tbody>
                            {columnInfo.sample_preview
                              .slice(0, 5)
                              .map((row, i) => (
                                <tr key={i}>
                                  {columnInfo.columns.map(col => (
                                    <td key={col} title={String(row[col] ?? '')}>
                                      {String(row[col] ?? '')}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                <div className="upload-mapping-footer">
                  <button
                    onClick={() => setStep('upload')}
                    className="upload-back-button"
                  >
                    <ArrowLeft size={16} />
                    Back
                  </button>

                  <button
                    onClick={handleConfirmMapping}
                    className="upload-continue-button"
                  >
                    Confirm mapping
                    <ArrowRight size={16} />
                  </button>
                </div>
              </>
            )}

            {/* STEP 3: CONFIRM */}
            {step === 'confirm' && (
              <div className="upload-confirm-content">
                <div className="upload-confirm-icon">
                  <FileCheck2 size={34} strokeWidth={1.5} />
                </div>

                <div className="upload-panel-kicker">
                  <CheckCircle2 size={14} />
                  CONFIGURATION COMPLETE
                </div>

                <h2>Your dataset is ready.</h2>

                <p>
                  Your file has been uploaded and its columns have been
                  mapped successfully. You can now begin the cleaning
                  process.
                </p>

                {file && (
                  <div className="upload-confirm-file">
                    <div className="upload-selected-file-icon">
                      <FileSpreadsheet size={20} />
                    </div>

                    <div className="upload-selected-file-info">
                      <strong>{file.name}</strong>
                      <span>{formatFileSize(file.size)}</span>
                    </div>

                    <CheckCircle2
                      size={19}
                      className="upload-file-success"
                    />
                  </div>
                )}

                <div className="upload-confirm-details">
                  <div>
                    <CheckCircle2 size={16} />
                    File successfully uploaded
                  </div>
                  <div>
                    <CheckCircle2 size={16} />
                    Column mapping saved
                  </div>
                  <div>
                    <CheckCircle2 size={16} />
                    Required review text field configured
                  </div>
                </div>

                <button
                  onClick={handleStartPipeline}
                  className="upload-continue-button upload-start-button"
                >
                  Start data cleaning
                  <ArrowRight size={18} />
                </button>

                <span className="upload-confirm-footnote">
                  NEXT: DATA CLEANING & QUALITY INSPECTION
                </span>
              </div>
            )}
          </section>

          {/* Right information panel */}
          <aside className="upload-side-panel">
            <div className="upload-side-top">
              <span className="upload-side-label">ALPHAEV / DATA INTELLIGENCE</span>

              <div className="upload-side-visual">
                <div className="upload-visual-orbit upload-orbit-one" />
                <div className="upload-visual-orbit upload-orbit-two" />
                <div className="upload-visual-center">
                  <Database size={28} strokeWidth={1.4} />
                </div>
                <span className="upload-visual-node node-one" />
                <span className="upload-visual-node node-two" />
                <span className="upload-visual-node node-three" />
              </div>

              <h3>
                From raw reviews
                <br />
                to meaningful insight.
              </h3>

              <p>
                AlphaEV organises unstructured EV charging feedback into
                evidence-backed intelligence.
              </p>
            </div>

            <div className="upload-side-divider" />

            <div className="upload-side-capabilities">
              <span className="upload-side-label">WHAT HAPPENS NEXT</span>

              <div className="upload-capability">
                <div className="upload-capability-icon">
                  <FileCheck2 size={17} />
                </div>
                <div>
                  <strong>Data cleaning</strong>
                  <span>Inspect and prepare raw reviews</span>
                </div>
              </div>

              <div className="upload-capability">
                <div className="upload-capability-icon">
                  <Columns3 size={17} />
                </div>
                <div>
                  <strong>Aspect classification</strong>
                  <span>Identify key EV experience topics</span>
                </div>
              </div>

              <div className="upload-capability">
                <div className="upload-capability-icon">
                  <Sparkles size={17} />
                </div>
                <div>
                  <strong>Explainable intelligence</strong>
                  <span>Explore patterns and customer sentiment</span>
                </div>
              </div>
            </div>

            <div className="upload-side-footer">
              <span className="upload-side-footer-dot" />
              BUILT FOR EV REVIEW INTELLIGENCE
            </div>
          </aside>
        </div>

        <footer className="upload-page-footer">
          <span>ALPHAEV</span>
          <span>EXPLAINABLE AI-POWERED EV REVIEW INTELLIGENCE</span>
        </footer>
      </div>
    </main>
  );
}
