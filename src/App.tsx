import React, { Component } from "react";
import flourish from "./data/flourish.json";
import metadata from "./data/metadata.json";
import { TopChanges } from "./TopChanges";

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
    return (
      <div className="center-column">
        <TopChanges
          flourish={new Map(Object.entries(flourish))}
          metadata={new Map(Object.entries(metadata))}
          dates={Object.keys(flourish)}
        />
      </div>
    );
  };
}
