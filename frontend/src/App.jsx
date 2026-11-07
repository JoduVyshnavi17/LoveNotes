
import React, { useEffect, useState } from 'react';
import { api } from './api';
import {
  BookOpen, Upload, FileText, LogOut, Plus, Search,
  RefreshCw, Download, Check, X, Archive, Trash2,
  Sparkles, Save, ChevronRight
} from 'lucide-react';

const PAGE_BREAK = '\n\n--- PAGE BREAK ---\n\n';

function joinPages(pages, field) {
  return (pages || []).map(p => p[field] || '').join(PAGE_BREAK);
}

function SourcePage({ page }) {
  const [src, setSrc] = useState('');

  useEffect(() => {
    let url;

    api(`/api/pages/${page.id}/image`)
      .then(blob => {
        url = URL.createObjectURL(blob);
        setSrc(url);
      })
      .catch(() => {});

    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [page.id]);

  return (
    <div className="source-card">
      <b>Page {page.page_number}</b>
      {src
        ? <img src={src} alt={`Original handwritten page ${page.page_number}`} />
        : <small>Loading source preview...</small>}
    </div>
  );
}

function Auth({ onAuth }) {
  const [mode, setMode] = useState('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [purpose, setPurpose] = useState('student');
  const [education, setEducation] = useState('');
  const [error, setError] = useState('');

  async function submit(e) {
    e.preventDefault();
    setError('');

    try {
      const d = await api(`/api/auth/${mode}`, {
        method: 'POST',
        body: mode === 'register'
          ? {
              full_name: name,
              email,
              password,
              confirm_password: confirmPassword,
              purpose,
              education_level: education
            }
          : { email, password }
      });

      localStorage.setItem('nm_token', d.access_token);
      onAuth(d.user);
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div className="auth">
      <form onSubmit={submit}>
        <div className="logo"><BookOpen /></div>
        <small>HANDWRITTEN NOTES, RECONSTRUCTED</small>
        <h1>{mode === 'login' ? 'Welcome back' : 'Create your account'}</h1>
        <p>Keep source notes faithful. Keep AI additions separate.</p>

        {mode === 'register' && (
          <>
            <label>
              Full name
              <input value={name} onChange={e => setName(e.target.value)}
                required minLength="2" />
            </label>

            <label>
              Purpose
              <select value={purpose} onChange={e => setPurpose(e.target.value)}>
                <option value="student">Student — study and revision</option>
                <option value="teacher">Teacher / Educator</option>
                <option value="professional">Professional / Work notes</option>
                <option value="personal learning">Personal learning</option>
                <option value="other">Other</option>
              </select>
            </label>

            <label>
              Class / course / field
              <input value={education}
                onChange={e => setEducation(e.target.value)}
                placeholder="e.g. B.Tech Computer Science" />
            </label>
          </>
        )}

        <label>
          Email
          <input type="email" value={email}
            onChange={e => setEmail(e.target.value)} required />
        </label>

        <label>
          Password
          <input type="password" value={password}
            onChange={e => setPassword(e.target.value)}
            required minLength={mode === 'register' ? 10 : 1} />
        </label>

        {mode === 'register' && (
          <label>
            Confirm password
            <input type="password" value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              required minLength={10} />
          </label>
        )}

        {error && <div className="error">{error}</div>}

        <button className="primary">
          {mode === 'login' ? 'Sign in' : 'Create account'}
        </button>

        <p className="switch">
          {mode === 'login' ? 'New here?' : 'Already registered?'}
          {' '}
          <button type="button"
            onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
            {mode === 'login' ? 'Create account' : 'Sign in'}
          </button>
        </p>
      </form>
    </div>
  );
}

/* Displays nested summary data as readable headings, lists and paragraphs. */
function ReadableContent({ data, depth = 0 }) {
  if (data === null || data === undefined) return null;

  if (typeof data === 'string' || typeof data === 'number') {
    return <p>{String(data)}</p>;
  }

  if (Array.isArray(data)) {
    return (
      <ul>
        {data.map((item, i) => (
          <li key={i}>
            {typeof item === 'object'
              ? <ReadableContent data={item} depth={depth + 1} />
              : String(item)}
          </li>
        ))}
      </ul>
    );
  }

  if (typeof data === 'object') {
    return (
      <div className="readable-content">
        {Object.entries(data).map(([key, value]) => {
          if (value === null || value === undefined || key === 'id') return null;

          const heading = key
            .replace(/_/g, ' ')
            .replace(/\b\w/g, c => c.toUpperCase());

          return (
            <section key={key} className="study-section">
              {typeof value === 'object'
                ? <h4>{heading}</h4>
                : <b>{heading}: </b>}
              <ReadableContent data={value} depth={depth + 1} />
            </section>
          );
        })}
      </div>
    );
  }

  return null;
}

function getQuizQuestions(content) {
  if (Array.isArray(content)) return content;
  if (Array.isArray(content?.questions)) return content.questions;
  if (Array.isArray(content?.quiz)) return content.quiz;
  if (Array.isArray(content?.items)) return content.items;
  return [];
}

function QuizView({ material }) {
  const questions = getQuizQuestions(material.content);
  const [answers, setAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);

  function choose(questionIndex, optionIndex) {
    if (submitted) return;

    setAnswers(prev => ({
      ...prev,
      [questionIndex]: optionIndex
    }));
  }

  function submitQuiz() {
    if (Object.keys(answers).length !== questions.length) {
      alert('Please answer every question before submitting.');
      return;
    }

    setSubmitted(true);
  }

  function resetQuiz() {
    setAnswers({});
    setSubmitted(false);
  }

  function getCorrectIndex(question) {
    if (Number.isInteger(question.answer_index)) {
      return question.answer_index;
    }

    if (Number.isInteger(question.correct_answer)) {
      return question.correct_answer;
    }

    if (typeof question.answer === 'number') {
      return question.answer;
    }

    if (typeof question.answer === 'string' && Array.isArray(question.options)) {
      return question.options.findIndex(
        option => String(option).trim() === question.answer.trim()
      );
    }

    return -1;
  }

  const score = questions.reduce((total, question, index) => {
    return total + (
      answers[index] === getCorrectIndex(question) ? 1 : 0
    );
  }, 0);

  if (!questions.length) {
    return (
      <div className="empty compact">
        Quiz data is unavailable or has an unexpected format.
      </div>
    );
  }

  return (
    <div className="quiz-view">
      <div className="quiz-meta">
        <b>{questions.length} questions</b>
        {submitted && (
          <b className="quiz-score">
            Score: {score}/{questions.length}
          </b>
        )}
      </div>

      {questions.map((question, index) => {
        const options = question.options || [];
        const correctIndex = getCorrectIndex(question);

        return (
          <div className="quiz-question" key={index}>
            <h4>
              {index + 1}. {question.question || question.text || 'Question'}
            </h4>

            <div className="quiz-options">
              {options.map((option, optionIndex) => {
                const selected = answers[index] === optionIndex;
                const correct = submitted && optionIndex === correctIndex;
                const wrong = submitted && selected && !correct;

                return (
                  <button
                    type="button"
                    key={optionIndex}
                    disabled={submitted}
                    onClick={() => choose(index, optionIndex)}
                    className={[
                      'quiz-option',
                      selected ? 'selected' : '',
                      correct ? 'correct' : '',
                      wrong ? 'incorrect' : ''
                    ].join(' ')}
                  >
                    <span>{String.fromCharCode(65 + optionIndex)}.</span>
                    {' '}{String(option)}
                    {correct && <Check size={16} />}
                    {wrong && <X size={16} />}
                  </button>
                );
              })}
            </div>

            {submitted && (
              <div className="quiz-feedback">
                {correctIndex >= 0 && (
                  <p>
                    <b>{answers[index] === correctIndex
                      ? 'Correct!'
                      : 'Incorrect.'}</b>
                    {' '}Correct answer:{' '}
                    {options[correctIndex] !== undefined
                      ? String(options[correctIndex])
                      : question.answer || 'Not provided'}
                  </p>
                )}
                {question.explanation && (
                  <p>{question.explanation}</p>
                )}
              </div>
            )}
          </div>
        );
      })}

      {!submitted ? (
        <button className="primary" onClick={submitQuiz}>
          Submit answers
        </button>
      ) : (
        <button className="primary" onClick={resetQuiz}>
          Try again
        </button>
      )}
    </div>
  );
}

function StudyMaterialView({ material }) {
  const isQuiz = material.kind === 'quiz';

  return (
    <div className="suggestion study-material">
      <div className="study-material-heading">
        <b>{isQuiz ? 'Practice quiz' : 'Study summary'}</b>
        <small>{material.created_at
          ? new Date(material.created_at).toLocaleString()
          : ''}</small>
      </div>

      {isQuiz
        ? <QuizView key={material.id} material={material} />
        : <ReadableContent data={material.content} />}
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [docs, setDocs] = useState([]);
  const [doc, setDoc] = useState(null);

  const [faithful, setFaithful] = useState('');
  const [enhanced, setEnhanced] = useState('');
  const [complete, setComplete] = useState('');

  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('faithful');
  const [depth, setDepth] = useState('detailed');

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  async function load() {
    setDocs(await api('/api/documents'));
  }

  useEffect(() => {
    if (localStorage.getItem('nm_token')) {
      api('/api/auth/me')
        .then(setUser)
        .catch(() => localStorage.removeItem('nm_token'));
    }
  }, []);

  useEffect(() => {
    if (user) load().catch(e => setError(e.message));
  }, [user]);

  async function open(id) {
    setError('');

    try {
      const d = await api(`/api/documents/${id}`);

      d.studyMaterials = await api(`/api/documents/${id}/study-aids`)
        .catch(() => []);

      setDoc(d);
      setFaithful(joinPages(d.pages, 'faithful_text'));
      setEnhanced(joinPages(d.pages, 'enhanced_text'));
      setComplete(joinPages(d.pages, 'complete_text'));
    } catch (e) {
      setError(e.message);
    }
  }

  async function upload(e) {
    const files = [...e.target.files];

    if (!files.length) return;

    const fd = new FormData();
    files.forEach(file => fd.append('files', file));

    setBusy(true);
    setError('');

    try {
      const d = await api('/api/documents/upload', {
        method: 'POST',
        body: fd
      });

      await load();
      await open(d.id);
      setMessage('Uploaded. Choose a workflow and process the pages.');
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
      e.target.value = '';
    }
  }

  async function process() {
    if (!doc) return;

    setBusy(true);
    setError('');
    setMessage('');

    try {
      const d = await api(
        `/api/documents/${doc.id}/process?mode=${mode}`,
        { method: 'POST' }
      );

      setDoc(d);
      setFaithful(joinPages(d.pages, 'faithful_text'));
      setEnhanced(joinPages(d.pages, 'enhanced_text'));
      setComplete(joinPages(d.pages, 'complete_text'));

      await load();

      const messages = {
        faithful: 'Faithful reconstruction completed.',
        enhanced: 'AI enhanced reconstruction completed.',
        complete: 'Complete My Notes generated.'
      };

      setMessage(
        `${messages[mode]} Verify the result against your original source pages.`
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    if (!doc) return;

    setBusy(true);
    setError('');

    try {
      await api(`/api/documents/${doc.id}/content`, {
        method: 'PATCH',
        body: {
          faithful_text: faithful,
          enhanced_text: enhanced,
          complete_text: complete
        }
      });

      await open(doc.id);
      setMessage('All three note sections saved successfully.');
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function makeStudyAid(kind) {
    if (!doc) return;

    setBusy(true);
    setError('');

    try {
      const item = await api(
        `/api/documents/${doc.id}/study-aids/${kind}`,
        { method: 'POST' }
      );

      setDoc(prev => ({
        ...prev,
        studyMaterials: [
          item,
          ...(prev.studyMaterials || []).filter(m => m.id !== item.id)
        ]
      }));

      setMessage(`${kind} generated and saved.`);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function makeSuggestions() {
    if (!doc) return;

    setBusy(true);
    setError('');

    try {
      const suggestions = await api(
        `/api/documents/${doc.id}/suggestions?depth=${depth}`,
        { method: 'POST' }
      );

      setDoc(prev => ({ ...prev, suggestions }));
      setMessage(`${suggestions.length} suggestions generated. Review each one.`);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function updateSuggestion(id, status) {
    try {
      await api(`/api/suggestions/${id}`, {
        method: 'PATCH',
        body: { status }
      });

      await open(doc.id);
    } catch (e) {
      setError(e.message);
    }
  }

  async function exportAs(format) {
    try {
      const blob = await api(
        `/api/documents/${doc.id}/export?format=${format}`,
        { method: 'POST' }
      );

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');

      a.href = url;
      a.download = `notemind.${format}`;
      a.click();

      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.message);
    }
  }

  async function remove(id) {
    if (!confirm('Permanently delete this notebook and its source pages?')) {
      return;
    }

    try {
      await api(`/api/documents/${id}`, { method: 'DELETE' });

      if (doc?.id === id) setDoc(null);

      await load();
    } catch (e) {
      setError(e.message);
    }
  }

  function signOut() {
    localStorage.removeItem('nm_token');
    setUser(null);
    setDoc(null);
    setDocs([]);
  }

  if (!user) return <Auth onAuth={setUser} />;

  const filtered = docs.filter(d =>
    d.title.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="layout">
      <aside>
        <div className="brand">
          <BookOpen />
          <b>LoveNotes</b>
        </div>

        <label className="upload-btn">
          <Plus /> New notebook
          <input
            type="file"
            accept=".jpg,.jpeg,.png,.webp,.pdf"
            multiple
            onChange={upload}
          />
        </label>

        <div className="navtitle">YOUR LIBRARY</div>
        <div className="navitem">
          <FileText /> All notebooks <span>{docs.length}</span>
        </div>

        <div className="profile">
          <div className="avatar">{user.full_name[0]}</div>
          <div>
            <b>{user.full_name}</b>
            <small>{user.email}</small>
          </div>
          <button title="Sign out" onClick={signOut}>
            <LogOut />
          </button>
        </div>
      </aside>

      <main>
        <header>
          <div>Private workspace <span className="dot" /></div>
          <span>Your notes, your language</span>
        </header>

        <section className="content">
          {error && (
            <div className="error">
              {error}
              <button onClick={() => setError('')}><X /></button>
            </div>
          )}

          {message && (
            <div className="success">
              {message}
              <button onClick={() => setMessage('')}><X /></button>
            </div>
          )}

          {!doc ? (
            <>
              <div className="hero">
                <small>YOUR PERSONAL STUDY & NOTES SPACE</small>
                <h1>Your notes deserve<br />to be understood.</h1>
                <p>
                  Upload handwritten notes in your language.
                  Reconstruct them faithfully, discover missing points,
                  and create summaries and practice quizzes.
                </p>

                <label className="primary hero-upload">
                  <Upload /> Upload notes
                  <input
                    type="file"
                    accept=".jpg,.jpeg,.png,.webp,.pdf"
                    multiple
                    onChange={upload}
                  />
                </label>
              </div>

              <div className="section-head">
                <div>
                  <h2>Your notebooks</h2>
                  <p>{docs.length} documents in your library</p>
                </div>

                <div className="search">
                  <Search />
                  <input
                    placeholder="Search notebooks"
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                  />
                </div>
              </div>

              {filtered.length ? (
                <div className="grid">
                  {filtered.map(d => (
                    <article onClick={() => open(d.id)} key={d.id}>
                      <div className="fileicon"><FileText /></div>

                      <button
                        className="delete"
                        onClick={e => {
                          e.stopPropagation();
                          remove(d.id);
                        }}
                      >
                        <Trash2 />
                      </button>

                      <h3>{d.title}</h3>
                      <p>{d.original_filename}</p>
                      <small>
                        {d.page_count} pages ·{' '}
                        {new Date(d.created_at).toLocaleDateString()}
                      </small>
                      <b className="open">
                        Open notebook <ChevronRight />
                      </b>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="empty">
                  <BookOpen />
                  <h3>No notebooks yet</h3>
                  <p>Upload a clear photo or scanned PDF to begin.</p>
                </div>
              )}
            </>
          ) : (
            <>
              <button className="back" onClick={() => setDoc(null)}>
                ← All notebooks
              </button>

              <div className="dochead">
                <div>
                  <h1>{doc.title}</h1>
                  <p>
                    {doc.pages.length} source pages · Original source kept separate
                  </p>
                </div>

                <div className="exports">
                  <button onClick={() => exportAs('pdf')}>
                    <Download /> PDF
                  </button>
                  <button onClick={() => exportAs('docx')}>DOCX</button>
                  <button onClick={() => exportAs('txt')}>TXT</button>
                </div>
              </div>

              <div className="toolbar">
                <label>
                  WORKFLOW
                  <select value={mode} onChange={e => setMode(e.target.value)}>
                    <option value="faithful">Faithful reconstruction</option>
                    <option value="enhanced">AI enhanced reconstruction</option>
                    <option value="complete">Complete my notes</option>
                  </select>
                </label>

                <button className="primary" disabled={busy} onClick={process}>
                  <RefreshCw />
                  {busy ? 'Processing...' : 'Process pages'}
                </button>
              </div>

              <div className="editgrid">
                <div className="panel">
                  <div className="paneltitle">
                    <div>
                      <small>SOURCE-BASED</small>
                      <h3>1. Faithful reconstruction</h3>
                    </div>
                    <span>Editable</span>
                  </div>

                  <p>
                    Exact transcription of your original notes.
                    No rewriting or additional explanations.
                  </p>

                  <textarea
                    value={faithful}
                    onChange={e => setFaithful(e.target.value)}
                    placeholder="Faithful transcription appears here. Unclear words should be marked [unclear]."
                  />
                </div>

                <div className="panel">
                  <div className="paneltitle">
                    <div>
                      <small>READABILITY</small>
                      <h3>2. AI enhanced reconstruction</h3>
                    </div>
                    <span className="purple">AI assisted</span>
                  </div>

                  <p>
                    Improves grammar, readability and organization
                    while preserving your original meaning and language.
                  </p>

                  <textarea
                    value={enhanced}
                    onChange={e => setEnhanced(e.target.value)}
                    placeholder="AI enhanced notes appear here after processing."
                  />
                </div>

                <div className="panel complete-panel">
                  <div className="paneltitle">
                    <div>
                      <small>ADDITIONAL LEARNING CONTENT</small>
                      <h3>3. Complete my notes</h3>
                    </div>
                    <span className="purple">AI expanded</span>
                  </div>

                  <p>
                    Keeps your original concepts and adds clearly
                    distinguishable explanations, definitions, examples
                    and missing subtopics.
                  </p>

                  <textarea
                    value={complete}
                    onChange={e => setComplete(e.target.value)}
                    placeholder="Complete notes appear here after choosing Complete my notes and processing."
                  />
                </div>
              </div>

              <div className="savebar">
                <p>Each version is stored separately. Your source images remain unchanged.</p>
                <button className="primary" onClick={save} disabled={busy}>
                  <Save /> Save all three sections
                </button>
              </div>

              <div className="panel">
                <div className="paneltitle">
                  <div>
                    <small>STUDENT STUDY TOOLS</small>
                    <h3>Study summary & practice quiz</h3>
                    <p>
                      Generated from your notes and saved with this notebook.
                    </p>
                  </div>

                  <div className="suggesttools">
                    <button
                      onClick={() => makeStudyAid('summary')}
                      disabled={busy}
                    >
                      Create summary
                    </button>

                    <button
                      onClick={() => makeStudyAid('quiz')}
                      disabled={busy}
                    >
                      Create quiz
                    </button>
                  </div>
                </div>

                {doc.studyMaterials?.length ? (
                  doc.studyMaterials.map(m => (
                    <StudyMaterialView key={m.id} material={m} />
                  ))
                ) : (
                  <div className="empty compact">
                    Create a study summary or practice quiz to begin.
                  </div>
                )}
              </div>

              <div className="panel">
                <div className="paneltitle">
                  <div>
                    <small>OPTIONAL AI REVIEW</small>
                    <h3>Possible missing points</h3>
                    <p>
                      Suggestions are not source facts. Verify before accepting.
                    </p>
                  </div>

                  <div className="suggesttools">
                    <select
                      value={depth}
                      onChange={e => setDepth(e.target.value)}
                    >
                      <option value="basic">Basic</option>
                      <option value="detailed">Detailed</option>
                      <option value="comprehensive">Comprehensive</option>
                    </select>

                    <button onClick={makeSuggestions} disabled={busy}>
                      <Sparkles /> Find gaps
                    </button>
                  </div>
                </div>

                {doc.suggestions?.length ? (
                  doc.suggestions.map(s => (
                    <div className="suggestion" key={s.id}>
                      <div className="suggestmeta">
                        <span>{s.category.replaceAll('_', ' ')}</span>
                        <small>
                          {Math.round(s.confidence * 100)}% model confidence
                        </small>
                      </div>

                      <h4>{s.title}</h4>
                      <p>{s.content}</p>
                      <small>{s.rationale}</small>

                      {s.evidence && (
                        <blockquote>
                          Evidence in notes: “{s.evidence}”
                        </blockquote>
                      )}

                      {s.status === 'pending' ? (
                        <div className="suggestbuttons">
                          <button onClick={() => updateSuggestion(s.id, 'accepted')}>
                            <Check /> Accept
                          </button>
                          <button onClick={() => updateSuggestion(s.id, 'rejected')}>
                            <X /> Reject
                          </button>
                        </div>
                      ) : (
                        <small>Marked {s.status}</small>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="empty compact">
                    Run Find gaps to generate optional suggestions.
                  </div>
                )}
              </div>

              <div className="panel">
                <small>UPLOADED MATERIAL</small>
                <h3>Source pages</h3>
                <div className="pages">
                  {doc.pages.map(p => (
                    <SourcePage key={p.id} page={p} />
                  ))}
                </div>
              </div>
            </>
          )}
        </section>
      </main>
    </div>
  );
}
