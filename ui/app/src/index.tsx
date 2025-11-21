import { App } from "./App";
import { mergeStyles } from "@fluentui/react";
import reportWebVitals from "./reportWebVitals";
import { BrowserRouter } from "react-router-dom";
import { pca } from "./authConfig";
import { MsalProvider } from "@azure/msal-react";
import { Provider } from "react-redux";
import { store } from "./store/store";
import { createRoot } from "react-dom/client";

// Inject some global styles
mergeStyles({
  ":global(body,html)": {
    margin: 0,
    padding: 0,
    height: "100vh",
  },
});

const root = createRoot(document.getElementById("root") as HTMLElement);

root.render(
  <MsalProvider instance={pca}>
    <BrowserRouter>
      <Provider store={store}>
        <App />
      </Provider>
    </BrowserRouter>
  </MsalProvider>,
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
