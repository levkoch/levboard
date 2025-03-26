import React, { Component, MouseEvent } from "react";
import { ReactComponent as Lemon } from "./image/lemon.svg";
import { ReactComponent as RightArrows } from "./image/right_arrows.svg";
import { ReactComponent as LeftArrows } from "./image/left_arrows.svg";

type EntryProps = {
  year: bigint;
  title: string;
  assets: Array<string>;
  description: string;
};

type EntryState = {
  selected: bigint;
};

type GalleryProps = {
  count: bigint;
  metadata: Map<string, EntryProps>;
};

type GalleryState = {
  entries: Array<EntryProps>;
  showing: bigint;
};

export class Gallery extends Component<GalleryProps, GalleryState> {
  constructor(props: GalleryProps) {
    super(props);
    this.state = { showing: 2n, entries: [] };
  }

  componentDidMount = () => {
    this.generateEntries();
  };

  render = (): JSX.Element => {
    if (this.state.entries.length === 0) {
      return <div>Loading galleries...</div>;
    }

    return (
      <div className="gallery">
        {this.state.entries.map((metadata, index) => (
          <GalleryEntry key={index} {...metadata} />
        ))}
      </div>
    );
  };

  onMoreClick = (_evt: MouseEvent<HTMLButtonElement>) => {
    if (this.state.showing < this.props.count) {
      var showing = this.state.showing + 2n;
      if (showing > this.props.count) {
        this.setState({ showing: this.props.count });
      } else {
        this.setState({ showing: showing });
      }
    }
  };

  generateEntries = (): void => {
    const entries: Array<EntryProps> = [];
    var i = 0n;
    while (i < this.props.count) {
      const metadata: EntryProps | undefined = this.props.metadata.get(
        String(i)
      );
      if (metadata === undefined) {
        throw Error("gallery length was wrong, shouldn't happen");
      }
      entries.push(metadata);
      i += 1n;
    }

    this.setState({ entries: entries });
  };
}

class GalleryEntry extends Component<EntryProps, EntryState> {
  constructor(props: EntryProps) {
    super(props);
    this.state = { selected: 0n };
  }

  render = () => {
    /* <!-- not the biggest fan of whatever the title is trying to be --> */
    return (
      <div className="gallery-entry">
        <div className="info-title">
          <Lemon className="lemon" />
          <span className="heading">{this.props.title}</span>
          <span className="years">{String(this.props.year)}</span>
        </div>

        <div className="gallery-main-group">
          <span className="gallery-b-container">
            <button className="gallery-button" onClick={this.onMoveLeft}>
              <LeftArrows />
            </button>
          </span>
          <img
            className="gallery-image"
            src={
              "levboard/gallery/" +
              this.props.assets[Number(this.state.selected)]
            }
          />
          <span className="gallery-b-container">
            <button className="gallery-button" onClick={this.onMoveRight}>
              <RightArrows />
            </button>
          </span>
        </div>
      </div>
    );
  };

  // bumps the image to the right
  onMoveRight = (_evt: MouseEvent<HTMLButtonElement>) => {
    const newSelected =
      (this.state.selected + 1n) % BigInt(this.props.assets.length);
    this.setState({ selected: newSelected });
  };

  // bumps the image to the left
  onMoveLeft = (_evt: MouseEvent<HTMLButtonElement>) => {
    const newSelected =
      // this is kinda dumb, but if we don't add the length of assets, it will be 
      // totally happy sending in a negative number, like -1 and -2 if we have 
      // three total items.
      (this.state.selected - 1n + BigInt(this.props.assets.length)) %
      BigInt(this.props.assets.length);
    this.setState({ selected: newSelected });
  };
}
