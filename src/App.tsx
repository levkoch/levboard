import React, { Component, MouseEvent } from "react";
import gallery from "./data/gallery.json";
import flourish from "./data/flourish.json";
import metadata from "./data/metadata.json";
import { TopChanges } from "./TopChanges";
import { Gallery } from "./Gallery";
import { TopPacked } from "./TopPacked";

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
      content = (<div>
        <TopChanges
          flourish={new Map(Object.entries(flourish))}
          metadata={new Map(Object.entries(metadata))}
          dates={Object.keys(flourish)}
        /> 
        <TopPacked 
        flourish={new Map(Object.entries(flourish))}
          metadata={new Map(Object.entries(metadata))}
          dates={Object.keys(flourish)}
          /></div>
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
      <>
        <nav className="nav-container">
          <a onClick={this.onNavClick("infographic")} className="nav-item">
            Featured
          </a>
          <a onClick={this.onNavClick("gallery")} className="nav-item">
            Gallery
          </a>
          <a onClick={this.onNavClick("about")} className="nav-item">
            About
          </a>
        </nav>
        <div className="center-column">{content}</div>
      </>
    );
  };

  onNavClick: (option: string) => (_evt: MouseEvent) => void = (option) => {
    return (_evt) => {
      console.log(`selected ${option}`);

      if (option === "gallery" || option === "infographic") {
        this.setState({ display: option });
      }
    };
  };
}
