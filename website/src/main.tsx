import React, { lazy, Suspense } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Site, type WebsiteBoot } from "./site";
const Editor = lazy(() =>
  import("./editor").then((module) => ({ default: module.Editor })),
);
import "./styles.css";
import "./reference.css";
import "./console.css";
const root = document.getElementById("root")!;
const bootstrap = document.getElementById("website-bootstrap");
const boot: WebsiteBoot = bootstrap
  ? JSON.parse(bootstrap.textContent || "{}")
  : {};
const app = (
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route
          path="/admin/*"
          element={
            <Suspense
              fallback={
                <main className="editor-login">
                  <p>Loading your owner workspace…</p>
                </main>
              }
            >
              <Editor />
            </Suspense>
          }
        />
        <Route path="*" element={<Site boot={boot} />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
if (root.dataset.ssr === "true") ReactDOM.hydrateRoot(root, app);
else ReactDOM.createRoot(root).render(app);
