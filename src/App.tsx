import React, { Component, MouseEvent } from "react";
import gallery from "./data/gallery.json";
import flourish from "./data/flourish.json";
import metadata from "./data/metadata.json";
import { TopChanges } from "./TopChanges";
import { Gallery } from "./Gallery";

type AppProps = {}; // no props

type AppState = {
  width?: bigint;
  display: "infographic" | "gallery";
};

/** THINSPO:
 * https://jsfiddle.net/8xdozwy4/
 */

/** Top-level component that displays the entire UI. */
export class App extends Component<AppProps, AppState> {
  constructor(props: AppProps) {
    super(props);

    this.state = {
      display: "infographic",
    };
  }

  render = (): JSX.Element => {
    let content: JSX.Element;
    if (this.state.display === "infographic") {
      content = (
        <TopChanges
          flourish={new Map(Object.entries(flourish))}
          metadata={new Map(Object.entries(metadata))}
          dates={Object.keys(flourish)}
        />
      );
    } else if (this.state.display === "gallery") {
      content = (
        <Gallery
          count={BigInt(gallery["count"])}
          metadata={new Map(Object.entries(gallery))}
        />
      );
    } else {
      content = <p>{"unknown state"}</p>;
    }

    return (
      <div>
        <span className="navigation">
          <button
            className="nav-button"
            id="nav-button-infographic"
            onClick={this.onNavClick("infographic")}
          >
            Featured
          </button>
          <button
            className="nav-button"
            id="nav-button-gallery"
            onClick={this.onNavClick("gallery")}
          >
            Gallery
          </button>
        </span>
        <div className="center-column">{content}</div>
      </div>
    );
  };

  onNavClick: (
    option: string
  ) => (_evt: MouseEvent<HTMLButtonElement>) => void = (option) => {
    return (_evt) => {
      console.log(`selected ${option}`);

      if (option === "gallery" || option === "infographic") {
        this.setState({ display: option });
      }
    };
  };
}
