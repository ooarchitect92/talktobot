import { renderToString } from "react-dom/server";
import { StaticRouter } from "react-router-dom";
import { Site, type WebsiteBoot } from "./site";

export function render(url: string, boot: WebsiteBoot) {
  return renderToString(
    <StaticRouter location={url}>
      <Site boot={boot} />
    </StaticRouter>,
  );
}
export { configureWebsiteOrigins } from './api';
